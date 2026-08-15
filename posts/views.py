from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from .models import Post
from .serializers import PostSerializer, PostCreateUpdateSerializer
from communities.models import Community, CommunityMember

User = get_user_model()


class PostListView(generics.ListCreateAPIView):
    """
    List all posts or create a new post
    """

    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        queryset = Post.objects.all().select_related("community", "user")
        community_id = self.request.query_params.get("community_id")
        user_id = self.request.query_params.get("user_id")

        if community_id:
            queryset = queryset.filter(community_id=community_id)
        if user_id:
            queryset = queryset.filter(user_id=user_id)

        return queryset

    def get_serializer_class(self):
        if self.request.method == "POST":
            return PostCreateUpdateSerializer
        return PostSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def perform_create(self, serializer):
        # If community_id is not in request data, check URL parameters
        community_id = self.request.data.get(
            "community_id"
        ) or self.request.query_params.get("community_id")
        community = None

        if community_id:
            community = get_object_or_404(Community, id=community_id)
        else:
            # If no community specified, raise error
            raise PermissionDenied("community_id is required to create a post.")

        # Check if user is a member of the community
        if not self._is_member(self.request.user, community):
            raise PermissionDenied(
                "You must be a member of this community to create posts."
            )

        serializer.save(user=self.request.user, community=community)

    def _is_member(self, user, community):
        if not user.is_authenticated:
            return False
        return CommunityMember.objects.filter(community=community, user=user).exists()


class PostDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a post
    """

    queryset = Post.objects.all().select_related("community", "user")
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return PostCreateUpdateSerializer
        return PostSerializer

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context

    def perform_update(self, serializer):
        post = self.get_object()

        # Check if user is the author
        if post.user != self.request.user:
            # Check if user is community owner/moderator
            if not self._has_moderator_permission(self.request.user, post.community):
                raise PermissionDenied("You don't have permission to update this post.")

        serializer.save()

    def perform_destroy(self, instance):
        # Check if user is the author
        if instance.user != self.request.user:
            # Check if user is community owner/moderator
            if not self._has_moderator_permission(
                self.request.user, instance.community
            ):
                raise PermissionDenied("You don't have permission to delete this post.")

        instance.delete()

    def _has_moderator_permission(self, user, community):
        if not user.is_authenticated:
            return False
        try:
            membership = CommunityMember.objects.get(community=community, user=user)
            return membership.role in [
                CommunityMember.Role.OWNER,
                CommunityMember.Role.MODERATOR,
            ]
        except CommunityMember.DoesNotExist:
            return False


class PostByCommunityView(generics.ListAPIView):
    """
    Get all posts for a specific community
    """

    serializer_class = PostSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        community_id = self.kwargs.get("community_id")
        return (
            Post.objects.filter(community_id=community_id)
            .select_related("community", "user")
            .order_by("-created_at")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context


class PostByUserView(generics.ListAPIView):
    """
    Get all posts by a specific user
    """

    serializer_class = PostSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        user_id = self.kwargs.get("user_id")
        return (
            Post.objects.filter(user_id=user_id)
            .select_related("community", "user")
            .order_by("-created_at")
        )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["request"] = self.request
        return context
