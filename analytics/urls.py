from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RepositoryStatsViewSet,
    UserStatsViewSet,
    UpdateLogViewSet,
    ContributorViewSet,
    ContributorActivityViewSet,
)

router = DefaultRouter()
router.register(
    r"repository-stats", RepositoryStatsViewSet, basename="repository-stats"
)
router.register(r"user-stats", UserStatsViewSet, basename="user-stats")
router.register(r"update-logs", UpdateLogViewSet, basename="update-logs")
router.register(r"contributors", ContributorViewSet, basename="contributors")
router.register(
    r"contributor-activities",
    ContributorActivityViewSet,
    basename="contributor-activities",
)  # Make sure this exists

urlpatterns = [
    path("", include(router.urls)),
]
