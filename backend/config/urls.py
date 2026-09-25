from django.contrib import admin
from django.http import HttpResponse
from django.urls import include, path


def robots(request):
    """The API and the Django admin login have no business in search results.
    The public website has its own robots.txt that invites Google in."""
    return HttpResponse("User-agent: *\nDisallow: /\n", content_type="text/plain")


urlpatterns = [
    path("robots.txt", robots),
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
]

# Uploaded documents are deliberately NOT served from /media/. Passports and
# bank statements are downloaded only through /api/documents/<id>/download/,
# which checks the person asking may see that student.

admin.site.site_header = "Banana Education"
admin.site.site_title = "Banana Education"
admin.site.index_title = "Manage content and students"
