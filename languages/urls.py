# languages/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import RepositoryLanguageViewSet

router = DefaultRouter()
router.register(r"", RepositoryLanguageViewSet, basename="languages")

urlpatterns = [
    path("", include(router.urls)),
]
