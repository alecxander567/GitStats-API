from django.urls import path
from .views import PostListView, PostDetailView, PostByCommunityView, PostByUserView

urlpatterns = [
    # List and create posts
    path("", PostListView.as_view(), name="post-list"),
    # Get, update, delete specific post
    path("<int:pk>/", PostDetailView.as_view(), name="post-detail"),
    # Get posts by community
    path(
        "community/<int:community_id>/",
        PostByCommunityView.as_view(),
        name="post-by-community",
    ),
    # Get posts by user
    path("user/<int:user_id>/", PostByUserView.as_view(), name="post-by-user"),
]
