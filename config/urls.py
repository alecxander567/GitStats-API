from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("users.urls")),
    path("api/repositories/", include("repositories.urls")),
    path("api/languages/", include("languages.urls")),
    path("api/analytics/", include("analytics.urls")),
    path("api/project-categories/", include("project_categories.urls")),
    path("api/communities/", include("communities.urls")),  # Add this line
    path("api/posts/", include("posts.urls")),
    path("api/readme-profile/", include("readme_profiles.urls")),
]
