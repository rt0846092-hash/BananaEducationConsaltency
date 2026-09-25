from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("core.urls")),
]

# Uploaded documents are deliberately NOT served from /media/. Passports and
# bank statements are downloaded only through /api/documents/<id>/download/,
# which checks the person asking may see that student.

admin.site.site_header = "Banana Education"
admin.site.site_title = "Banana Education"
admin.site.index_title = "Manage content and students"
