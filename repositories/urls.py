from django.urls import path
from .views import (
    RepositoryListView,
    RepositoryDetailView,
    RepositoryStatsView,
    BulkCreateRepositoriesView,
    RepositoryLanguagesView,
    RepositoryUserCommitsView,  # ADD THIS
)

urlpatterns = [
    path("", RepositoryListView.as_view(), name="repository-list"),
    path("<int:pk>/", RepositoryDetailView.as_view(), name="repository-detail"),
    path("stats/", RepositoryStatsView.as_view(), name="repository-stats"),
    path("bulk/", BulkCreateRepositoriesView.as_view(), name="repository-bulk-create"),
    path("languages/", RepositoryLanguagesView.as_view(), name="repository-languages"),
    path(
        "<int:pk>/user-commits/",
        RepositoryUserCommitsView.as_view(),
        name="repository-user-commits",
    ),  # ADD THIS
]
