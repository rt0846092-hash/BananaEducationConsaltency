from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenRefreshView

from . import owner_api, views

# Owner-only management (staff and website content) — see core/owner_api.py
owner = DefaultRouter(trailing_slash=True)
owner.include_root_view = False
owner.register("staff", owner_api.StaffViewSet, basename="staff")
owner.register("countries", owner_api.CountryAdminViewSet, basename="manage-country")
owner.register("universities", owner_api.UniversityAdminViewSet, basename="manage-university")
owner.register("courses", owner_api.CourseAdminViewSet, basename="manage-course")
owner.register("scholarships", owner_api.ScholarshipAdminViewSet, basename="manage-scholarship")
owner.register("batches", owner_api.BatchAdminViewSet, basename="manage-batch")

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
    path("leads/<int:pk>/delete/", views.delete_lead),
    path("manage/", include(owner.urls)),
]