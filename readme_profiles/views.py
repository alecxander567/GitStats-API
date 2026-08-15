from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.viewsets import ModelViewSet
from django.http import HttpResponse
from django.utils import timezone
from .models import ReadmeProfile, ReadmeTemplate, ReadmeGenerationHistory
from .serializers import ReadmeProfileSerializer, ReadmeTemplateSerializer
from .services import ReadmeGenerator


class ReadmeProfileViewSet(ModelViewSet):
    """ViewSet for managing README profiles"""

    serializer_class = ReadmeProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return ReadmeProfile.objects.filter(user=self.request.user)

    def get_or_create_profile(self):
        """Get or create a profile for the current user"""
        profile, created = ReadmeProfile.objects.get_or_create(
            user=self.request.user,
            defaults={
                "content": "",
                "template": "modern",
                "settings": {
                    "show_stats": True,
                    "show_languages": True,
                    "show_contributions": True,
                    "show_activity_chart": True,
                    "show_badges": True,
                },
            },
        )
        return profile

    def list(self, request, *args, **kwargs):
        """Get the user's profile"""
        profile = self.get_or_create_profile()
        serializer = self.get_serializer(profile)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """Update the user's profile"""
        profile = self.get_or_create_profile()
        serializer = self.get_serializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def regenerate(self, request):
        """Manually regenerate the README"""
        try:
            # Get or create profile
            profile = self.get_or_create_profile()

            # Generate content, honoring this profile's show_* toggles
            generator = ReadmeGenerator(request.user)
            generated_content = generator.generate(profile_settings=profile.settings)

            # Update profile with generated content
            profile.content = generated_content
            profile.last_generated = timezone.now()
            profile.save()

            # Create history entry
            ReadmeGenerationHistory.objects.create(
                profile=profile, status="success", content_length=len(generated_content)
            )

            return Response(
                {
                    "status": "success",
                    "content": generated_content,
                    "last_generated": profile.last_generated,
                }
            )
        except Exception as e:
            # Log the error
            import traceback

            traceback.print_exc()

            # Create failed history entry if profile exists
            try:
                profile = self.get_or_create_profile()
                ReadmeGenerationHistory.objects.create(
                    profile=profile, status="failed", error_message=str(e)
                )
            except Exception:
                pass

            return Response(
                {"status": "error", "message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

    @action(detail=False, methods=["get"])
    def export(self, request):
        """Download the README as a .md file"""
        profile = self.get_or_create_profile()
        generator = ReadmeGenerator(request.user)

        # Generate fresh content, honoring this profile's show_* toggles
        content = generator.generate(profile_settings=profile.settings)

        # Update last_generated
        profile.last_generated = timezone.now()
        profile.export_count += 1
        profile.save()

        # Create HTTP response with markdown file
        response = HttpResponse(content, content_type="text/markdown; charset=utf-8")
        response["Content-Disposition"] = (
            f'attachment; filename="README_{request.user.username}.md"'
        )

        return response

    @action(detail=False, methods=["get"])
    def preview(self, request):
        """Preview the README with current data"""
        profile = self.get_or_create_profile()
        generator = ReadmeGenerator(request.user)

        content = generator.generate(profile_settings=profile.settings)

        return Response(
            {
                "content": content,
                "user": request.user.username,
                "last_generated": profile.last_generated,
            }
        )

    @action(detail=False, methods=["post"])
    def toggle_auto_update(self, request):
        """Enable or disable auto-updates"""
        profile = self.get_or_create_profile()
        profile.auto_update_enabled = not profile.auto_update_enabled

        if profile.auto_update_enabled:
            profile.schedule_next_update()

        profile.save()

        return Response(
            {
                "auto_update_enabled": profile.auto_update_enabled,
                "next_update": profile.next_update,
            }
        )

    @action(detail=False, methods=["get"])
    def templates(self, request):
        """Get available templates"""
        templates = ReadmeTemplate.objects.filter(is_active=True)
        serializer = ReadmeTemplateSerializer(templates, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def history(self, request):
        """Get generation history"""
        profile = self.get_or_create_profile()
        history = profile.generation_history.all()[:20]
        data = [
            {
                "generated_at": h.generated_at,
                "status": h.status,
                "error_message": h.error_message,
                "content_length": h.content_length,
            }
            for h in history
        ]
        return Response(data)
