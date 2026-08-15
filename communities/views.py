from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from .models import Community, CommunityMember
from .serializers import (
    CommunitySerializer, 
    CommunityCreateUpdateSerializer,
    CommunityMemberSerializer,
    AddMemberSerializer,
    UpdateMemberRoleSerializer
)

User = get_user_model()

# ======================
# COMMUNITY VIEWS
# ======================

class CommunityListView(generics.ListCreateAPIView):
    """
    List all communities or create a new community
    """
    queryset = Community.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        if self.request.method == 'POST':
            return CommunityCreateUpdateSerializer
        return CommunitySerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def perform_create(self, serializer):
        """
        Save the community with the current user as creator
        """
        community = serializer.save(created_by=self.request.user)
        # Add the creator as an owner
        CommunityMember.objects.create(
            community=community,
            user=self.request.user,
            role=CommunityMember.Role.OWNER
        )


class CommunityDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a community
    """
    queryset = Community.objects.all()
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_serializer_class(self):
        if self.request.method in ['PUT', 'PATCH']:
            return CommunityCreateUpdateSerializer
        return CommunitySerializer
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def perform_update(self, serializer):
        """
        Check if user is the creator or an owner before updating
        """
        instance = self.get_object()
        if not self._has_permission(self.request.user, instance):
            raise PermissionDenied("You don't have permission to update this community.")
        serializer.save()
    
    def perform_destroy(self, instance):
        """
        Check if user is the creator or an owner before deleting
        """
        if not self._has_permission(self.request.user, instance):
            raise PermissionDenied("You don't have permission to delete this community.")
        instance.delete()
    
    def _has_permission(self, user, community):
        """Check if user has permission (creator or owner)"""
        if user == community.created_by:
            return True
        try:
            membership = CommunityMember.objects.get(community=community, user=user)
            return membership.role in [CommunityMember.Role.OWNER, CommunityMember.Role.MODERATOR]
        except CommunityMember.DoesNotExist:
            return False


class CommunityBySlugView(generics.RetrieveAPIView):
    """
    Retrieve a community by its slug
    """
    serializer_class = CommunitySerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'slug'
    lookup_url_kwarg = 'slug'
    queryset = Community.objects.all()
    
    def get_serializer_context(self):
        context = super().get_serializer_context()
        context['request'] = self.request
        return context


# ======================
# COMMUNITY MEMBER VIEWS
# ======================

class CommunityMemberViewSet(viewsets.ModelViewSet):
    """
    ViewSet for community members
    """
    queryset = CommunityMember.objects.all()
    serializer_class = CommunityMemberSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    
    def get_queryset(self):
        """Filter members by community if community_id is provided"""
        queryset = CommunityMember.objects.all()
        community_id = self.request.query_params.get('community_id')
        user_id = self.request.query_params.get('user_id')
        role = self.request.query_params.get('role')
        
        if community_id:
            queryset = queryset.filter(community_id=community_id)
        if user_id:
            queryset = queryset.filter(user_id=user_id)
        if role:
            queryset = queryset.filter(role=role)
        
        return queryset.select_related('user', 'community')
    
    def create(self, request, *args, **kwargs):
        """Add a member to a community"""
        serializer = AddMemberSerializer(
            data=request.data,
            context={'community_id': request.data.get('community_id')}
        )
        serializer.is_valid(raise_exception=True)
        
        data = serializer.validated_data
        community = get_object_or_404(Community, id=data['community_id'])
        user = get_object_or_404(User, id=data['user_id'])
        
        # Check if the current user has permission (owner or moderator)
        if not self._has_permission(request.user, community):
            return Response(
                {"detail": "You don't have permission to add members to this community"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        member = CommunityMember.objects.create(
            community=community,
            user=user,
            role=data.get('role', CommunityMember.Role.MEMBER)
        )
        
        return Response(
            CommunityMemberSerializer(member).data,
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        """Update a member's role"""
        member = self.get_object()
        community = member.community
        
        # Check if the current user has permission (owner or moderator)
        if not self._has_permission(request.user, community):
            return Response(
                {"detail": "You don't have permission to update members in this community"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Only owners can change roles (including promoting/demoting)
        if not self._is_owner(request.user, community):
            return Response(
                {"detail": "Only owners can change member roles"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = UpdateMemberRoleSerializer(
            data=request.data,
            context={'community_id': community.id, 'user_id': member.user.id}
        )
        serializer.is_valid(raise_exception=True)
        
        member.role = serializer.validated_data['role']
        member.save()
        
        return Response(CommunityMemberSerializer(member).data)
    
    def destroy(self, request, *args, **kwargs):
        """Remove a member from a community"""
        member = self.get_object()
        community = member.community
        
        # Check if the current user has permission (owner or moderator)
        if not self._has_permission(request.user, community):
            return Response(
                {"detail": "You don't have permission to remove members from this community"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Check if trying to remove the last owner
        if member.role == CommunityMember.Role.OWNER:
            owner_count = CommunityMember.objects.filter(
                community=community,
                role=CommunityMember.Role.OWNER
            ).count()
            
            if owner_count == 1:
                return Response(
                    {"detail": "Cannot remove the last owner of the community"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        member.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'])
    def my_communities(self, request):
        """Get communities where the current user is a member"""
        if not request.user.is_authenticated:
            return Response(
                {"detail": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        memberships = CommunityMember.objects.filter(
            user=request.user
        ).select_related('community')
        
        # Return community details instead of membership details
        communities = []
        for membership in memberships:
            community_data = CommunitySerializer(
                membership.community, 
                context={'request': request}
            ).data
            community_data['user_role'] = membership.role
            community_data['user_role_display'] = membership.get_role_display()
            community_data['joined_at'] = membership.joined_at
            communities.append(community_data)
        
        return Response(communities)
    
    @action(detail=False, methods=['get'])
    def community_members(self, request):
        """Get all members of a specific community"""
        community_id = request.query_params.get('community_id')
        if not community_id:
            return Response(
                {"detail": "community_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        members = CommunityMember.objects.filter(
            community_id=community_id
        ).select_related('user')
        
        serializer = CommunityMemberSerializer(members, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def user_communities(self, request):
        """Get all communities a specific user belongs to"""
        user_id = request.query_params.get('user_id')
        if not user_id:
            return Response(
                {"detail": "user_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        memberships = CommunityMember.objects.filter(
            user_id=user_id
        ).select_related('community')
        
        data = [{
            'community_id': m.community.id,
            'community_name': m.community.name,
            'community_slug': m.community.slug,
            'role': m.role,
            'role_display': m.get_role_display(),
            'joined_at': m.joined_at
        } for m in memberships]
        
        return Response(data)
    
    # Helper methods
    def _has_permission(self, user, community):
        """Check if user has permission to manage members (owner or moderator)"""
        if not user.is_authenticated:
            return False
        try:
            membership = CommunityMember.objects.get(
                community=community,
                user=user
            )
            return membership.role in [
                CommunityMember.Role.OWNER,
                CommunityMember.Role.MODERATOR
            ]
        except CommunityMember.DoesNotExist:
            return False
    
    def _is_owner(self, user, community):
        """Check if user is an owner of the community"""
        if not user.is_authenticated:
            return False
        try:
            membership = CommunityMember.objects.get(
                community=community,
                user=user
            )
            return membership.role == CommunityMember.Role.OWNER
        except CommunityMember.DoesNotExist:
            return False