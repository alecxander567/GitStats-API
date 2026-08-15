from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CommunityListView, CommunityDetailView, CommunityBySlugView, CommunityMemberViewSet

# Create a router for the viewset
router = DefaultRouter()
router.register(r'members', CommunityMemberViewSet, basename='community-members')

urlpatterns = [
    # Community URLs
    path('', CommunityListView.as_view(), name='community-list'),
    path('<int:pk>/', CommunityDetailView.as_view(), name='community-detail'),
    path('slug/<slug:slug>/', CommunityBySlugView.as_view(), name='community-by-slug'),
    
    # Community Member URLs (via router)
    path('', include(router.urls)),
]