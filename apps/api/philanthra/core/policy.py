"""Fail-closed source and derivative policy; no staff or superuser bypass."""

from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from .models import Artifact, DataGrant, Membership, Source

PURPOSES = {"benchmarking", "pooled_analysis", "donor_access", "publication", "external_ai"}
WRITE_ROLES = {"owner", "administrator", "analyst", "editor"}
ADMIN_ROLES = {"owner", "administrator"}


def workspace_for(request, *, write=False, admin=False):
    if not request.user.is_authenticated:
        raise PermissionDenied("Authentication required.")
    selected = request.headers.get("X-Workspace-ID")
    memberships = Membership.objects.filter(user=request.user).select_related("workspace")
    try:
        membership = (
            memberships.filter(workspace_id=selected).first()
            if selected
            else memberships.order_by("created_at").first()
        )
    except (ValueError, DjangoValidationError) as exc:
        raise NotFound() from exc
    if membership is None:
        raise NotFound()
    if admin and membership.role not in ADMIN_ROLES:
        raise PermissionDenied("Workspace owner or administrator required.")
    if write and membership.role not in WRITE_ROLES:
        raise PermissionDenied("Read-only membership.")
    return membership.workspace


def matching_grant(source, workspace, purpose, cause, geography):
    if purpose not in PURPOSES or not cause or not geography or source.state != "active":
        return None
    grants = source.grants.filter(active=True, purpose=purpose, cause=cause, geography=geography)
    now = timezone.now()
    for grant in grants.order_by("id"):
        if grant.expires_at and grant.expires_at <= now:
            continue
        if grant.audience == "workspace" and grant.recipient_id != getattr(workspace, "id", None):
            continue
        if grant.audience not in {"workspace", "public"}:
            continue
        if purpose == "external_ai" and not grant.external_processing:
            continue
        return grant
    return None


def can_source(source, workspace, purpose="donor_access", cause=None, geography=None):
    if source.state != "active":
        return False
    if source.owner_id is None:
        return source.kind in {"public_source", "synthetic_demo"} and purpose != "external_ai"
    if workspace and source.owner_id == workspace.id and purpose != "external_ai":
        return True
    return (
        matching_grant(
            source, workspace, purpose, cause or source.cause, geography or source.geography
        )
        is not None
    )


def dependency_current(dep):
    if dep.source.state != "active" or dep.source.revision != dep.source_revision:
        return False
    if dep.grant_id:
        grant = dep.grant
        if (
            not grant.active
            or grant.revision != dep.grant_revision
            or (grant.expires_at and grant.expires_at <= timezone.now())
        ):
            return False
    return True


def reviewer_scope_allowed(artifact, reviewer):
    """Owner delegation covers own sources; third-party sources retain recipient limits."""
    if not reviewer or not reviewer.is_active:
        return False
    dependencies = list(artifact.dependencies.select_related("source", "grant"))
    return any(
        all(
            dependency_current(dep)
            and (
                dep.source.owner_id in {None, artifact.owner_id}
                or can_source(
                    dep.source,
                    membership.workspace,
                    artifact.purpose,
                    artifact.cause,
                    artifact.geography,
                )
            )
            for dep in dependencies
        )
        for membership in Membership.objects.filter(user=reviewer, role="reviewer").select_related(
            "workspace"
        )
    )


def can_artifact(artifact, workspace, *, user=None, allow_review=True):
    if artifact.status in {"invalidated", "withdrawn"}:
        return False
    deps = list(artifact.dependencies.select_related("source", "grant"))
    if not deps or not all(dependency_current(d) for d in deps):
        return False
    if artifact.kind == "analysis" and artifact.status == "approved":
        review = (
            artifact.decisions.filter(revision=artifact.revision, decision="approved")
            .order_by("-created_at")
            .first()
        )
        if review is None:
            return False
        recorded = review.snapshot.get("publication_grants", [])
        if {item.get("source_id") for item in recorded} != {
            str(d.source_id) for d in deps if d.source.owner_id is not None
        }:
            return False
        for item in recorded:
            grant = DataGrant.objects.filter(
                pk=item.get("id"), revision=item.get("revision"), active=True
            ).first()
            if grant is None or (grant.expires_at and grant.expires_at <= timezone.now()):
                return False
    is_owner = workspace and artifact.owner_id == workspace.id
    assigned = bool(
        allow_review
        and user
        and artifact.assignments.filter(reviewer=user, revision=artifact.revision).exists()
        and reviewer_scope_allowed(artifact, user)
    )
    if is_owner or assigned:
        return all(
            can_source(
                d.source, artifact.owner, artifact.purpose, artifact.cause, artifact.geography
            )
            for d in deps
        )
    if artifact.status != "approved":
        return False
    if artifact.kind == "analysis":
        if not all(
            d.source.owner_id is None
            or matching_grant(
                d.source, workspace, "publication", artifact.cause, artifact.geography
            )
            is not None
            for d in deps
        ):
            return False
    purposes = [artifact.purpose]
    if artifact.kind == "card" and workspace and workspace.kind == "ngo":
        purposes.append("benchmarking")
    return any(
        all(
            can_source(d.source, workspace, purpose, artifact.cause, artifact.geography)
            for d in deps
        )
        for purpose in purposes
    )


def visible_artifacts(workspace, *, kind=None, user=None):
    query = Artifact.objects.select_related("owner").prefetch_related(
        "dependencies__source", "dependencies__grant"
    )
    if kind:
        query = query.filter(kind=kind)
    return [a for a in query.order_by("-created_at") if can_artifact(a, workspace, user=user)]


def can_alert(alert, workspace):
    if alert.state == "invalidated" or not can_artifact(alert.artifact, workspace):
        return False
    if alert.target_source_id:
        if (
            alert.target_source.state != "active"
            or alert.target_source.revision != alert.target_source_revision
            or alert.target_program is None
        ):
            return False
        return all(
            can_source(
                dep.source,
                workspace,
                "benchmarking",
                alert.target_program.cause,
                alert.target_program.geography,
            )
            for dep in alert.artifact.dependencies.select_related("source")
        )
    return True


def artifact_attributions(artifact, workspace):
    """Attribution travels with both computation consent and recipient-specific access."""
    if artifact.kind == "analysis" and artifact.payload.get("status") != "draft":
        return []
    rows = []
    seen = set()
    for dep in artifact.dependencies.select_related("source", "grant"):
        grants = [dep.grant] if dep.grant_id else []
        grants.append(
            matching_grant(
                dep.source, workspace, artifact.purpose, artifact.cause, artifact.geography
            )
        )
        if artifact.kind == "card" and workspace and workspace.kind == "ngo":
            grants.append(
                matching_grant(
                    dep.source, workspace, "benchmarking", artifact.cause, artifact.geography
                )
            )
        if artifact.kind == "analysis":
            grants.append(
                matching_grant(
                    dep.source, workspace, "publication", artifact.cause, artifact.geography
                )
            )
        for grant in grants:
            if grant and grant.attribution and (dep.source_id, grant.attribution) not in seen:
                seen.add((dep.source_id, grant.attribution))
                rows.append({"source_id": str(dep.source_id), "text": grant.attribution})
    return rows


def source_or_404(source_id, workspace, purpose="donor_access"):
    from django.shortcuts import get_object_or_404

    source = get_object_or_404(Source, pk=source_id)
    if not can_source(source, workspace, purpose):
        raise NotFound()
    return source


def artifact_or_404(artifact_id, workspace, user=None, kind=None):
    from django.shortcuts import get_object_or_404

    artifact = get_object_or_404(Artifact, pk=artifact_id)
    if (kind and artifact.kind != kind) or not can_artifact(artifact, workspace, user=user):
        raise NotFound()
    return artifact


def validate_grant(data):
    unknown = set(data) - {
        "source_id",
        "purpose",
        "recipient_id",
        "audience",
        "cause",
        "geography",
        "expires_at",
        "attribution",
        "external_processing",
    }
    if unknown:
        raise ValidationError({"grant": "Unsupported restrictions or fields."})
    if data.get("purpose") not in PURPOSES or data.get("audience", "workspace") not in {
        "workspace",
        "public",
    }:
        raise ValidationError({"grant": "Unsupported purpose or audience."})
    if not data.get("cause") or not data.get("geography"):
        raise ValidationError({"grant": "Explicit cause and geography are required."})
    if data.get("audience", "workspace") == "workspace" and not data.get("recipient_id"):
        raise ValidationError({"recipient_id": "A recipient is required."})
    if data.get("audience") == "public" and data.get("recipient_id"):
        raise ValidationError(
            {"recipient_id": "Public audience cannot carry a recipient restriction."}
        )
    if data.get("purpose") == "external_ai" and data.get("external_processing") is not True:
        raise ValidationError(
            {"external_processing": "Separate affirmative permission is required."}
        )
