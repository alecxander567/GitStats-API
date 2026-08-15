from django.core.management.base import BaseCommand
from repositories.models import Repository
from project_categories.models import ProjectCategory
import re


class Command(BaseCommand):
    help = "Automatically categorize repositories based on their languages and metadata"

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Force update even if categories already exist",
        )
        parser.add_argument(
            "--repository-id",
            type=int,
            help="Only categorize a specific repository by ID",
        )
        parser.add_argument(
            "--min-confidence",
            type=float,
            default=30.0,
            help="Minimum confidence threshold (default: 30.0)",
        )
        parser.add_argument(
            "--fix-game",
            action="store_true",
            help="Fix repositories incorrectly categorized as Game",
        )

    def handle(self, *args, **options):
        force = options["force"]
        repo_id = options["repository_id"]
        min_confidence = options["min_confidence"]
        fix_game = options.get("fix_game", False)

        if fix_game:
            self.fix_game_categories()
            return

        if repo_id:
            repositories = Repository.objects.filter(id=repo_id)
            if not repositories.exists():
                self.stdout.write(
                    self.style.ERROR(f"Repository with ID {repo_id} not found")
                )
                return
        else:
            repositories = Repository.objects.all()

        category_rules = {
            "Web": {
                "patterns": [
                    r"web",
                    r"website",
                    r"frontend",
                    r"front-end",
                    r"backend",
                    r"back-end",
                    r"react",
                    r"vue",
                    r"angular",
                    r"svelte",
                    r"next\.?js",
                    r"nuxt",
                    r"django",
                    r"flask",
                    r"express",
                    r"node\.?js",
                    r"html",
                    r"css",
                    r"javascript",
                    r"typescript",
                    r"fullstack",
                    r"full-stack",
                    r"crud",
                    r"blog",
                    r"portfolio",
                    r"e-commerce",
                    r"shop",
                    r"store",
                    r"dashboard",
                    r"admin",
                    r"laravel",
                    r"php",
                ],
                "weight": 3,
                "name_boost": True,
                "language_boost": [
                    "javascript",
                    "typescript",
                    "html",
                    "css",
                    "php",
                    "django",
                    "flask",
                    "react",
                    "vue",
                ],
            },
            "Mobile": {
                "patterns": [
                    r"mobile",
                    r"app",
                    r"android",
                    r"ios",
                    r"iphone",
                    r"ipad",
                    r"react-native",
                    r"flutter",
                    r"swift",
                    r"kotlin",
                    r"android studio",
                    r"expo",
                    r"capacitor",
                    r"ionic",
                    r"xamarin",
                    r"ui",
                    r"android app",
                    r"ios app",
                    r"mobile app",
                ],
                "weight": 4,
                "name_boost": True,
                "language_boost": ["swift", "kotlin", "dart", "react-native"],
            },
            "Desktop": {
                "patterns": [
                    r"desktop",
                    r"windows",
                    r"macos",
                    r"linux",
                    r"electron",
                    r"tauri",
                    r"qt",
                    r"gtk",
                    r"win32",
                    r"winforms",
                    r"wpf",
                    r"slint",
                    r"desktop app",
                    r"download",
                    r"installer",
                    r"setup",
                ],
                "weight": 4,
                "name_boost": True,
                "language_boost": ["c++", "c#", "rust", "electron"],
            },
            "AI": {
                "patterns": [
                    r"ai",
                    r"artificial[- ]?intelligence",
                    r"machine[- ]?learning",
                    r"ml",
                    r"deep[- ]?learning",
                    r"neural",
                    r"transformer",
                    r"llm",
                    r"gpt",
                    r"tensorflow",
                    r"pytorch",
                    r"keras",
                    r"nlp",
                    r"computer[- ]?vision",
                    r"data[- ]?science",
                    r"analytics",
                    r"prediction",
                    r"classification",
                    r"recommendation",
                    r"sentiment",
                    r"chatbot",
                    r"intelligent",
                    r"auto",
                    r"smart",
                ],
                "weight": 5,
                "name_boost": True,
                "language_boost": ["python", "tensorflow", "pytorch", "keras"],
            },
            "API": {
                "patterns": [
                    r"api",
                    r"rest",
                    r"restful",
                    r"graphql",
                    r"grpc",
                    r"microservice",
                    r"service",
                    r"endpoint",
                    r"gateway",
                    r"proxy",
                    r"websocket",
                    r"fastapi",
                    r"apollo",
                    r"swagger",
                    r"openapi",
                ],
                "weight": 4,
                "name_boost": True,
                "language_boost": [
                    "python",
                    "javascript",
                    "typescript",
                    "go",
                    "rust",
                    "java",
                ],
            },
            "CLI": {
                "patterns": [
                    r"cli",
                    r"command[- ]?line",
                    r"terminal",
                    r"console",
                    r"shell",
                    r"bash",
                    r"script",
                    r"cmd",
                    r"tool",
                    r"utility",
                    r"automation",
                    r"cobra",
                    r"click",
                    r"argparse",
                ],
                "weight": 4,
                "name_boost": True,
                "language_boost": ["python", "go", "rust", "bash", "shell"],
            },
            "IoT": {
                "patterns": [
                    r"iot",
                    r"internet[- ]?of[- ]?things",
                    r"arduino",
                    r"esp32",
                    r"esp8266",
                    r"sensor",
                    r"raspberry[- ]?pi",
                    r"embedded",
                    r"firmware",
                    r"mqtt",
                    r"bluetooth",
                    r"ble",
                    r"zigbee",
                    r"microcontroller",
                    r"fingerprint",
                    r"biometric",
                ],
                "weight": 5,
                "name_boost": True,
                "language_boost": ["c++", "c", "python", "java"],
            },
            "Game": {
                "patterns": [
                    r"game",
                    r"gaming",
                    r"play",
                    r"player",
                    r"2d",
                    r"3d",
                    r"unity",
                    r"unreal",
                    r"godot",
                    r"pygame",
                    r"cocos",
                    r"phaser",
                    r"game[- ]?engine",
                    r"opengl",
                    r"vulkan",
                    r"directx",
                    r"raylib",
                    r"puzzle",
                    r"platformer",
                    r"level",
                    r"word[- ]?search",
                ],
                "weight": 5,
                "name_boost": True,
                "language_boost": ["c#", "c++", "python", "java", "unity", "unreal"],
            },
            "Library": {
                "patterns": [
                    r"library",
                    r"sdk",
                    r"wrapper",
                    r"binding",
                    r"toolkit",
                    r"package",
                    r"module",
                    r"pip",
                    r"npm",
                    r"crates",
                    r"gem",
                    r"composer",
                    r"lib",
                    r"api[- ]?wrapper",
                    r"client",
                ],
                "weight": 4,
                "name_boost": True,
                "language_boost": ["python", "javascript", "java", "c#", "go"],
            },
        }

        created_count = 0
        updated_count = 0
        skipped_count = 0
        other_count = 0

        for repo in repositories:
            self.stdout.write(f"Processing: {repo.full_name}")

            repo_languages = []
            if hasattr(repo, "languages"):
                try:
                    repo_languages = [
                        lang.name.lower() for lang in repo.languages.all()
                    ]
                except:
                    pass

            primary_lang_lower = (
                repo.primary_language.lower() if repo.primary_language else ""
            )
            if primary_lang_lower:
                repo_languages.append(primary_lang_lower)

            repo_name = repo.name.lower()
            repo_description = repo.description.lower() if repo.description else ""

            category_scores = {}

            for category, rules in category_rules.items():
                score = 0
                matches = []

                name_matches = 0
                for pattern in rules["patterns"]:
                    if re.search(pattern, repo_name, re.IGNORECASE):
                        name_matches += 1
                        matches.append(f"name:{pattern}")

                if rules.get("name_boost", False):
                    score += name_matches * rules["weight"] * 2
                else:
                    score += name_matches * rules["weight"]

                desc_matches = 0
                for pattern in rules["patterns"]:
                    if re.search(pattern, repo_description, re.IGNORECASE):
                        desc_matches += 1
                        matches.append(f"desc:{pattern}")

                score += desc_matches * (rules["weight"] // 2)

                lang_matches = 0
                for language in repo_languages:
                    for boost_lang in rules.get("language_boost", []):
                        if boost_lang in language:
                            lang_matches += 1
                            matches.append(f"lang:{boost_lang}")

                    for pattern in rules["patterns"]:
                        if re.search(pattern, language, re.IGNORECASE):
                            lang_matches += 1
                            matches.append(f"lang:{pattern}")

                score += lang_matches * rules["weight"]

                if primary_lang_lower:
                    for boost_lang in rules.get("language_boost", []):
                        if boost_lang in primary_lang_lower:
                            score += rules["weight"]
                            matches.append(f"primary:{boost_lang}")

                if category == "Web" and re.search(
                    r"web|website|blog|portfolio|crud|react|django|laravel|php",
                    repo_name,
                    re.IGNORECASE,
                ):
                    score += 10
                    matches.append("name_boost:web_clear")

                if category == "Mobile" and re.search(
                    r"mobile|android|ios|app|react-native|flutter",
                    repo_name,
                    re.IGNORECASE,
                ):
                    score += 10
                    matches.append("name_boost:mobile_clear")

                if category == "AI" and re.search(
                    r"ai|ml|learning|neural|gpt|smart|auto", repo_name, re.IGNORECASE
                ):
                    score += 10
                    matches.append("name_boost:ai_clear")

                if category == "IoT" and re.search(
                    r"esp32|arduino|sensor|iot|fingerprint|biometric",
                    repo_name,
                    re.IGNORECASE,
                ):
                    score += 10
                    matches.append("name_boost:iot_clear")

                if category == "Game" and re.search(
                    r"game|word-search|puzzle|platformer", repo_name, re.IGNORECASE
                ):
                    score += 10
                    matches.append("name_boost:game_clear")

                if category == "CLI" and re.search(
                    r"cli|script|terminal|bash|shell", repo_name, re.IGNORECASE
                ):
                    score += 10
                    matches.append("name_boost:cli_clear")

                if category == "Library" and re.search(
                    r"library|sdk|wrapper|package|module", repo_name, re.IGNORECASE
                ):
                    score += 10
                    matches.append("name_boost:library_clear")

                if category == "API" and re.search(
                    r"api|rest|graphql|grpc", repo_name, re.IGNORECASE
                ):
                    score += 10
                    matches.append("name_boost:api_clear")

                if category == "Desktop" and re.search(
                    r"desktop|electron|windows|macos|linux", repo_name, re.IGNORECASE
                ):
                    score += 10
                    matches.append("name_boost:desktop_clear")

                if score > 0:
                    category_scores[category] = {"score": score, "matches": matches[:8]}

            if category_scores:
                sorted_categories = sorted(
                    category_scores.items(), key=lambda x: x[1]["score"], reverse=True
                )
                best_category, best_data = sorted_categories[0]
                best_score = best_data["score"]

                max_possible_score = 80
                confidence = min((best_score / max_possible_score) * 100, 100)

                if confidence < min_confidence:
                    self.stdout.write(
                        f"  Best match {best_category} only has {confidence:.1f}% confidence (below {min_confidence}%)"
                    )
                    self.stdout.write(
                        f"     Matches: {', '.join(best_data['matches'])}"
                    )
                    skipped_count += 1
                    continue

                try:
                    obj, created = ProjectCategory.objects.update_or_create(
                        repository=repo,
                        category=best_category,
                        defaults={"confidence": round(confidence, 2)},
                    )

                    if created:
                        created_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  Created: {best_category} ({confidence:.1f}%)"
                            )
                        )
                        self.stdout.write(
                            f"     Matches: {', '.join(best_data['matches'][:5])}"
                        )
                    else:
                        updated_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  Updated: {best_category} ({confidence:.1f}%)"
                            )
                        )
                        self.stdout.write(
                            f"     Matches: {', '.join(best_data['matches'][:5])}"
                        )

                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  Error: {str(e)}"))

            else:
                try:
                    obj, created = ProjectCategory.objects.update_or_create(
                        repository=repo, category="Other", defaults={"confidence": 5.0}
                    )
                    other_count += 1
                    if created:
                        self.stdout.write(f"  Assigned: Other (5%)")
                    else:
                        self.stdout.write(f"  Updated: Other (5%)")
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f"  Error: {str(e)}"))

        self.stdout.write("\n" + "=" * 50)
        self.stdout.write(self.style.SUCCESS(f"Completed!"))
        self.stdout.write(f"   Created: {created_count} categories")
        self.stdout.write(f"   Updated: {updated_count} categories")
        self.stdout.write(f"   Assigned as 'Other': {other_count}")
        self.stdout.write(f"   Skipped (low confidence): {skipped_count}")
        self.stdout.write("=" * 50)

    def fix_game_categories(self):
        """Fix repositories that were incorrectly categorized as Game"""
        from project_categories.models import ProjectCategory

        game_categories = ProjectCategory.objects.filter(category="Game")
        fixed_count = 0

        for game_cat in game_categories:
            repo = game_cat.repository
            repo_name = repo.name.lower()
            repo_description = repo.description.lower() if repo.description else ""

            new_category = None

            if re.search(
                r"web|website|frontend|react|vue|angular|html|css|blog|portfolio",
                repo_name,
            ):
                new_category = "Web"
            elif re.search(r"mobile|android|ios|app|react-native|flutter", repo_name):
                new_category = "Mobile"
            elif re.search(r"desktop|electron|windows|macos", repo_name):
                new_category = "Desktop"
            elif (
                re.search(r"ai|ml|learning|neural|smart|auto|python", repo_name)
                and repo.primary_language
                and "python" in repo.primary_language.lower()
            ):
                new_category = "AI"
            elif re.search(r"esp32|arduino|sensor|iot", repo_name):
                new_category = "IoT"
            elif re.search(r"script|cli|bash|shell", repo_name):
                new_category = "CLI"
            elif re.search(r"api|rest|graphql", repo_name):
                new_category = "API"
            elif re.search(r"library|sdk|package|module", repo_name):
                new_category = "Library"

            if new_category:
                game_cat.category = new_category
                game_cat.confidence = max(game_cat.confidence, 40.0)
                game_cat.save()
                fixed_count += 1
                self.stdout.write(f"  Fixed: {repo.full_name} -> {new_category}")

        self.stdout.write(
            self.style.SUCCESS(
                f"Fixed {fixed_count} incorrectly categorized repositories"
            )
        )
