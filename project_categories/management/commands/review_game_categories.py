from django.core.management.base import BaseCommand
from project_categories.models import ProjectCategory
from repositories.models import Repository


class Command(BaseCommand):
    help = "Review repositories categorized as Game and suggest better categories"

    def add_arguments(self, parser):
        parser.add_argument(
            "--auto-fix",
            action="store_true",
            help="Automatically fix repositories that have clear alternative categories",
        )
        parser.add_argument(
            "--list-only",
            action="store_true",
            help="Only list the Game repositories without fixing",
        )

    def handle(self, *args, **options):
        auto_fix = options.get("auto_fix", False)
        list_only = options.get("list_only", False)

        game_categories = ProjectCategory.objects.filter(
            category="Game"
        ).select_related("repository")

        if list_only:
            self.stdout.write(
                f"\nFound {game_categories.count()} repositories categorized as Game:"
            )
            self.stdout.write("=" * 80)
            for cat in game_categories:
                repo = cat.repository
                self.stdout.write(f"  {repo.full_name}")
                self.stdout.write(
                    f"    Primary Language: {repo.primary_language or 'None'}"
                )
                self.stdout.write(
                    f"    Description: {repo.description or 'No description'}"
                )
                self.stdout.write(f"    Confidence: {cat.confidence}%")
                self.stdout.write("-" * 40)
            return

        self.stdout.write(
            f"\nReviewing {game_categories.count()} repositories categorized as Game..."
        )
        self.stdout.write("=" * 80)

        fixed_count = 0
        reviewed_count = 0

        for game_cat in game_categories:
            repo = game_cat.repository
            repo_name = repo.name.lower()
            repo_description = repo.description.lower() if repo.description else ""
            primary_lang = (
                repo.primary_language.lower() if repo.primary_language else ""
            )

            # Determine a better category based on patterns
            new_category = None
            confidence_boost = 0

            # Check for Web patterns
            web_patterns = [
                "web",
                "website",
                "frontend",
                "react",
                "vue",
                "angular",
                "html",
                "css",
                "blog",
                "portfolio",
                "crud",
                "dashboard",
                "admin",
                "laravel",
                "php",
            ]
            if any(pattern in repo_name for pattern in web_patterns):
                new_category = "Web"
                confidence_boost = 20

            # Check for Mobile patterns
            mobile_patterns = [
                "mobile",
                "android",
                "ios",
                "react-native",
                "flutter",
                "swift",
                "kotlin",
            ]
            if any(pattern in repo_name for pattern in mobile_patterns):
                new_category = "Mobile"
                confidence_boost = 25

            # Check for Desktop patterns
            desktop_patterns = [
                "desktop",
                "electron",
                "windows",
                "macos",
                "linux",
                "qt",
                "gtk",
            ]
            if any(pattern in repo_name for pattern in desktop_patterns):
                new_category = "Desktop"
                confidence_boost = 25

            # Check for AI patterns
            ai_patterns = ["ai", "ml", "learning", "neural", "gpt", "smart", "auto"]
            if any(pattern in repo_name for pattern in ai_patterns):
                new_category = "AI"
                confidence_boost = 20

            # Check for IoT patterns
            iot_patterns = [
                "esp32",
                "arduino",
                "sensor",
                "iot",
                "fingerprint",
                "biometric",
            ]
            if any(pattern in repo_name for pattern in iot_patterns):
                new_category = "IoT"
                confidence_boost = 25

            # Check for CLI patterns
            cli_patterns = ["cli", "script", "terminal", "bash", "shell", "cmd", "tool"]
            if any(pattern in repo_name for pattern in cli_patterns):
                new_category = "CLI"
                confidence_boost = 20

            # Check for API patterns
            api_patterns = ["api", "rest", "graphql", "grpc", "service"]
            if any(pattern in repo_name for pattern in api_patterns):
                new_category = "API"
                confidence_boost = 20

            # Check for Library patterns
            library_patterns = ["library", "sdk", "wrapper", "package", "module", "lib"]
            if any(pattern in repo_name for pattern in library_patterns):
                new_category = "Library"
                confidence_boost = 20

            # Special case: if it has "app" in the name but not mobile-specific
            if "app" in repo_name and not new_category:
                # Check if it's a web app
                if (
                    "web" in repo_name
                    or "react" in repo_name
                    or "angular" in repo_name
                    or "vue" in repo_name
                ):
                    new_category = "Web"
                    confidence_boost = 15
                # Check if it's a mobile app
                elif (
                    "mobile" in repo_name
                    or "android" in repo_name
                    or "ios" in repo_name
                ):
                    new_category = "Mobile"
                    confidence_boost = 15
                # Check if it's a desktop app
                elif "desktop" in repo_name or "electron" in repo_name:
                    new_category = "Desktop"
                    confidence_boost = 15

            # If it's a Java project, and not clearly anything else, it might be a Game
            if new_category is None and primary_lang == "java":
                # But Java could be many things - check description
                if repo_description:
                    if any(
                        pattern in repo_description
                        for pattern in ["game", "play", "gaming"]
                    ):
                        # Keep as Game if description mentions games
                        new_category = None
                    elif any(
                        pattern in repo_description
                        for pattern in ["web", "spring", "rest"]
                    ):
                        new_category = "Web"
                        confidence_boost = 15
                    elif any(
                        pattern in repo_description for pattern in ["mobile", "android"]
                    ):
                        new_category = "Mobile"
                        confidence_boost = 15
                    elif any(
                        pattern in repo_description for pattern in ["api", "service"]
                    ):
                        new_category = "API"
                        confidence_boost = 15
                    else:
                        # If it's just a Java project, might be Library or keep as Game
                        new_category = "Library"
                        confidence_boost = 10

            # If still Game, but it doesn't have game-related terms, consider recategorizing
            if new_category is None:
                # Check if it actually has game-related terms
                game_terms = [
                    "game",
                    "play",
                    "gaming",
                    "puzzle",
                    "word-search",
                    "2d",
                    "3d",
                ]
                if not any(term in repo_name for term in game_terms):
                    # If no game terms, it might be misclassified
                    if primary_lang:
                        if primary_lang in ["python", "javascript", "typescript"]:
                            new_category = "Web"
                            confidence_boost = 10
                        elif primary_lang in ["c#", "c++"]:
                            new_category = "Desktop"
                            confidence_boost = 10
                        elif primary_lang in ["java"]:
                            new_category = "Library"
                            confidence_boost = 10
                    else:
                        # If no language and no game terms, mark as Other
                        new_category = "Other"
                        confidence_boost = 5

            if auto_fix and new_category:
                # Update the category
                old_category = game_cat.category
                game_cat.category = new_category
                game_cat.confidence = min(game_cat.confidence + confidence_boost, 95)
                game_cat.save()
                fixed_count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Fixed: {repo.full_name} -> {new_category} (was {old_category}, confidence: {game_cat.confidence}%)"
                    )
                )
            elif new_category:
                self.stdout.write(f"  {repo.full_name}")
                self.stdout.write(f"    Current: Game ({game_cat.confidence}%)")
                self.stdout.write(
                    f"    Suggested: {new_category} (+{confidence_boost}% confidence)"
                )
                self.stdout.write(f"    Language: {repo.primary_language or 'None'}")
                self.stdout.write("-" * 40)
                reviewed_count += 1
            else:
                self.stdout.write(
                    f"  {repo.full_name} - Keep as Game (legitimate game or unknown)"
                )
                self.stdout.write(f"    Language: {repo.primary_language or 'None'}")
                self.stdout.write(
                    f"    Description: {repo.description or 'No description'}"
                )
                self.stdout.write("-" * 40)

        if auto_fix:
            self.stdout.write(self.style.SUCCESS(f"\nFixed {fixed_count} repositories"))
        else:
            self.stdout.write(f"\nSuggested changes for {reviewed_count} repositories")
            self.stdout.write("Run with --auto-fix to apply these changes")
