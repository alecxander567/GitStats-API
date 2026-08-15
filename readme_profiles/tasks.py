from celery import shared_task
from django.utils import timezone
from django.db import transaction
from .models import ReadmeProfile, ReadmeGenerationHistory
from .services import ReadmeGenerator


@shared_task
def update_all_readme_profiles():
    """Update all README profiles that are due for update"""
    profiles = ReadmeProfile.objects.filter(
        auto_update_enabled=True, is_active=True, next_update__lte=timezone.now()
    )

    results = []
    for profile in profiles:
        try:
            result = update_single_readme_profile.delay(profile.id)
            results.append(result)
        except Exception as e:
            print(f"Failed to update profile {profile.id}: {e}")

    return {"total_profiles": profiles.count(), "queued_tasks": len(results)}


@shared_task
def update_single_readme_profile(profile_id):
    """Update a single README profile"""
    from .models import ReadmeProfile, ReadmeGenerationHistory

    try:
        profile = ReadmeProfile.objects.get(id=profile_id)
    except ReadmeProfile.DoesNotExist:
        return {"status": "failed", "error": "Profile not found"}

    # Create history entry
    history = ReadmeGenerationHistory.objects.create(
        profile=profile, status="in_progress"
    )

    try:
        generator = ReadmeGenerator(profile.user)
        generated_content = generator.generate()

        # Save the generated content
        profile.last_generated = timezone.now()
        profile.schedule_next_update()

        with transaction.atomic():
            profile.save()
            history.status = "success"
            history.content_length = len(generated_content)
            history.save()

        return {
            "status": "success",
            "profile_id": profile.id,
            "content_length": len(generated_content),
        }

    except Exception as e:
        history.status = "failed"
        history.error_message = str(e)
        history.save()

        return {"status": "failed", "profile_id": profile.id, "error": str(e)}
