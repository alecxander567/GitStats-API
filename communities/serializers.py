from rest_framework import serializers
from .models import Community, CommunityMember
from django.contrib.auth import get_user_model
from django.utils.text import slugify

User = get_user_model()

class CommunitySerializer(serializers.ModelSerializer):
    """
    Community serializer for list and detail views
    """
    created_by_username = serializers.CharField(source='created_by.username', read_only=True)
    created_by_display_name = serializers.CharField(source='created_by.display_name', read_only=True)
    created_by_id = serializers.IntegerField(source='created_by.id', read_only=True)
    member_count = serializers.SerializerMethodField()
    user_role = serializers.SerializerMethodField()
    
    class Meta:
        model = Community
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'cover_image',
            'icon',
            'language',
            'created_by',
            'created_by_id',
            'created_by_username',
            'created_by_display_name',
            'created_at',
            'updated_at',
            'member_count',
            'user_role'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']
    
    def get_member_count(self, obj):
        return obj.memberships.count()
    
    def get_user_role(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                membership = obj.memberships.get(user=request.user)
                return membership.role
            except CommunityMember.DoesNotExist:
                return None
        return None

class CommunityCreateUpdateSerializer(serializers.ModelSerializer):
    """
    Serializer for create and update operations
    """
    class Meta:
        model = Community
        fields = [
            'id',
            'name',
            'slug',
            'description',
            'cover_image',
            'icon',
            'language',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'slug', 'created_at', 'updated_at']
    
    def validate_name(self, value):
        """
        Ensure name is not empty and has minimum length
        """
        if not value or len(value.strip()) < 3:
            raise serializers.ValidationError("Community name must be at least 3 characters long.")
        return value.strip()
    
    def validate_slug(self, value):
        """
        Ensure slug is unique if provided
        """
        if value:
            value = slugify(value)
            if Community.objects.filter(slug=value).exists():
                raise serializers.ValidationError("A community with this slug already exists.")
        return value
    
    def create(self, validated_data):
        """
        Set the created_by field to the current user
        """
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
        return super().create(validated_data)


# ======================
# COMMUNITY MEMBER SERIALIZERS
# ======================

class CommunityMemberSerializer(serializers.ModelSerializer):
    """
    Serializer for community members
    """
    username = serializers.CharField(source='user.username', read_only=True)
    email = serializers.EmailField(source='user.email', read_only=True)
    user_id = serializers.IntegerField(source='user.id', read_only=True)
    display_name = serializers.CharField(source='user.display_name', read_only=True)
    avatar_url = serializers.CharField(source='user.avatar_url', read_only=True)
    role_display = serializers.CharField(source='get_role_display', read_only=True)
    
    class Meta:
        model = CommunityMember
        fields = ['id', 'community', 'user', 'user_id', 'username', 'email', 
                 'display_name', 'avatar_url', 'role', 'role_display', 'joined_at']
        read_only_fields = ['id', 'joined_at', 'username', 'email', 'user_id', 'display_name', 'avatar_url', 'role_display']


class AddMemberSerializer(serializers.Serializer):
    """
    Serializer for adding a member to a community
    """
    community_id = serializers.IntegerField(required=True)
    user_id = serializers.IntegerField(required=True)
    role = serializers.ChoiceField(
        choices=CommunityMember.Role.choices,
        required=False,
        default=CommunityMember.Role.MEMBER
    )

    def validate_community_id(self, value):
        if not Community.objects.filter(id=value).exists():
            raise serializers.ValidationError("Community does not exist")
        return value

    def validate_user_id(self, value):
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User does not exist")
        return value
    
    def validate(self, data):
        community_id = data.get('community_id')
        user_id = data.get('user_id')
        
        # Check if user is already a member
        if CommunityMember.objects.filter(
            community_id=community_id, 
            user_id=user_id
        ).exists():
            raise serializers.ValidationError("User is already a member of this community")
        
        return data


class UpdateMemberRoleSerializer(serializers.Serializer):
    """
    Serializer for updating a member's role
    """
    role = serializers.ChoiceField(choices=CommunityMember.Role.choices, required=True)
    
    def validate(self, data):
        # Prevent removing the last owner
        community_id = self.context.get('community_id')
        user_id = self.context.get('user_id')
        
        if data['role'] != CommunityMember.Role.OWNER:
            # Check if this user is the only owner
            owner_count = CommunityMember.objects.filter(
                community_id=community_id,
                role=CommunityMember.Role.OWNER
            ).count()
            
            is_owner = CommunityMember.objects.filter(
                community_id=community_id,
                user_id=user_id,
                role=CommunityMember.Role.OWNER
            ).exists()
            
            if is_owner and owner_count == 1:
                raise serializers.ValidationError(
                    "Cannot change the last owner's role. Please assign another owner first."
                )
        
        return data