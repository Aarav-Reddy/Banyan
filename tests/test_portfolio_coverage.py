from philanthra.core import models as m
from philanthra.core.coverage import geographic_coverage
from philanthra.core.services import create_artifact
from philanthra.core.tests import DomainFixture


class CoverageTests(DomainFixture):
    def test_public_area_gaps_overlap_unknown_and_withdrawal(self):
        artifact = create_artifact(
            self.ws, self.owner, kind="portfolio", title="Coverage plan", sources=[self.source]
        )
        portfolio = m.Portfolio.objects.create(artifact=artifact, budget_cents=300)
        peer = m.Organization.objects.create(name="Second fictional NGO")
        unknown = m.Organization.objects.create(name="Unknown service geography")
        outside = m.Organization.objects.create(name="Not selected NGO")
        for org in [self.org, peer, unknown]:
            m.Allocation.objects.create(
                portfolio=portfolio, organization=org, amount_cents=100, cap_cents=100
            )
        public = self.source_for()
        shared = m.Geography.objects.create(
            code="shared", name="Reported shared area", source=public
        )
        gap = m.Geography.objects.create(code="gap", name="Reported other area", source=public)
        private = m.Geography.objects.create(
            code="secret", name="Private area title", source=self.source
        )
        headquarters = m.Geography.objects.create(
            code="hq", name="Headquarters only", source=public
        )
        for org, area, source, basis in [
            (self.org, shared, public, "synthetic_reported"),
            (peer, shared, public, "verified"),
            (outside, gap, public, "reported"),
            (unknown, private, self.source, "reported"),
            (unknown, headquarters, public, "headquarters"),
        ]:
            m.ServiceArea.objects.create(
                organization=org, geography=area, source=source, basis=basis
            )
        result = geographic_coverage(portfolio)
        rows = {a["code"]: a for a in result["areas"]}
        self.assertEqual(set(rows), {"shared", "gap"})
        self.assertEqual(rows["shared"]["status"], "potential_collaboration")
        self.assertEqual(len(rows["shared"]["selected_organizations"]), 2)
        self.assertEqual(rows["gap"]["status"], "not_represented_in_plan")
        self.assertEqual(result["unknown_service_area_organizations"][0]["id"], str(unknown.id))
        self.assertNotIn("Private area title", str(result))
        self.assertNotIn("amount_cents", str(rows))
        response = self.client.get(f"/api/v1/portfolios/{artifact.id}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            len(response.json()["data"]["portfolio"]["geographic_coverage"]["areas"]), 2
        )
        self.client.force_authenticate(self.other)
        self.client.credentials(HTTP_X_WORKSPACE_ID=str(self.donor.id))
        self.assertEqual(self.client.get(f"/api/v1/portfolios/{artifact.id}/").status_code, 404)
        public.state = "withdrawn"
        public.save()
        withdrawn = geographic_coverage(portfolio)
        self.assertEqual(withdrawn["areas"], [])
        self.assertEqual(len(withdrawn["unknown_service_area_organizations"]), 3)
        self.assertEqual(withdrawn["sources"], [])
