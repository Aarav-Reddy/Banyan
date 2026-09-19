from django.urls import path

from . import views as v
from .schema import apply_schema

urlpatterns = [
    path("workspaces/", v.WorkspacesView.as_view()),
    path("identity-claims/", v.IdentityClaimsView.as_view()),
    path("identity-claims/<uuid:pk>/proof/", v.IdentityProofView.as_view()),
    path("password-reset/request/", v.PasswordResetRequestView.as_view()),
    path("password-reset/confirm/", v.PasswordResetConfirmView.as_view()),
    path("bookmarks/", v.BookmarksView.as_view()),
    path("bookmarks/<uuid:pk>/", v.BookmarkDetailView.as_view()),
    path("watchlist/", v.WatchlistView.as_view()),
    path("watchlist/<uuid:pk>/", v.WatchDetailView.as_view()),
    path("monitor/", v.MonitorView.as_view()),
    path("impact-report/", v.ImpactReportView.as_view()),
    path("benchmark/", v.BenchmarkView.as_view()),
    path("profile/", v.ProfileView.as_view()),
    path("contact/", v.ContactView.as_view()),
    path("introductions/", v.IntroductionInboxView.as_view()),
    path("introductions/<uuid:pk>/decision/", v.IntroductionDecisionView.as_view()),
    path("introductions/<uuid:pk>/contact/", v.IntroductionContactView.as_view()),
]

apply_schema()
