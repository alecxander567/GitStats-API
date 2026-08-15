from django.contrib import admin
from .models import Community, CommunityMember

@admin.register(Community)
class CommunityAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'slug', 'created_by', 'member_count', 'created_at', 'updated_at']
    search_fields = ['name', 'description']
    list_filter = ['created_at', 'updated_at', 'language']
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ['id', 'created_at', 'updated_at']
    fields = ['id', 'name', 'slug', 'description', 'cover_image', 'icon', 
              'language', 'created_by', 'created_at', 'updated_at']
    
    def member_count(self, obj):
        return obj.memberships.count()
    member_count.short_description = 'Members'


@admin.register(CommunityMember)
class CommunityMemberAdmin(admin.ModelAdmin):
    list_display = ['id', 'community', 'user', 'role', 'joined_at']
    list_filter = ['role', 'joined_at']
    search_fields = ['community__name', 'user__username', 'user__email']
    readonly_fields = ['id', 'joined_at']
    raw_id_fields = ['community', 'user']
    ordering = ['-joined_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('community', 'user')