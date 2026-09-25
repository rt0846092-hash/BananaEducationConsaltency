from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

urlpatterns = [
    # Public — no login required
    path("countries/", views.CountryList.as_view()),
    path("countries/<slug:slug>/", views.CountryDetail.as_view()),
    path("batches/", views.BatchList.as_view()),
    path("counsellors/", views.CounsellorList.as_view()),
    path("leads/intake/", views.lead_intake),
    path("leads/intake/details/", views.lead_intake_details),

    # Staff — login required
    path("auth/login/", views.Login.as_view()),
    path("auth/refresh/", TokenRefreshView.as_view()),
    path("me/", views.me),
    path("auth/password/", views.change_password),
    path("leads/", views.LeadList.as_view()),
    path("leads/<int:pk>/", views.LeadDetail.as_view()),
    path("leads/<int:pk>/notes/", views.add_note),
    path("leads/<int:pk>/applications/", views.add_application),
    path("leads/<int:pk>/documents/", views.upload_document),
    path("applications/<int:pk>/", views.update_application),
    path("documents/<int:pk>/", views.document_detail),
    path("documents/<int:pk>/download/", views.download_document),
    path("universities/", views.university_options),
    path("dashboard/", views.dashboard),

    # Owner only
    path("team/", views.team),
    path("team/handover/", views.handover),
    path("reports/", views.reports),
    path("leads/export/", views.export_leads),
]