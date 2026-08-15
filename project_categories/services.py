from .models import ProjectCategory
from repositories.models import Repository
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


class CategoryService:
    """Service for categorizing repositories"""

    def __init__(self):
        self.category_map = self._get_category_map()
        # Pre-sort keys longest-first so multi-word/more specific keys
        # (e.g. "react native") win over short, generic ones (e.g. "c", "r")
        # when we fall back to substring matching.
        self._sorted_keys = sorted(self.category_map, key=len, reverse=True)

    def _get_category_map(self):
        """Get the mapping of languages to categories - matching the model choices"""
        return {
            # Web Development
            "html": "Web",
            "css": "Web",
            "javascript": "Web",
            "typescript": "Web",
            "react": "Web",
            "vue": "Web",
            "angular": "Web",
            "svelte": "Web",
            "nextjs": "Web",
            "nuxt": "Web",
            "tailwind": "Web",
            "bootstrap": "Web",
            "django": "Web",
            "flask": "Web",
            "fastapi": "Web",
            "node": "Web",
            "express": "Web",
            "php": "Web",
            "laravel": "Web",
            "ruby": "Web",
            "rails": "Web",
            # Mobile Development
            "swift": "Mobile",
            "flutter": "Mobile",
            "react native": "Mobile",
            "android": "Mobile",
            "ios": "Mobile",
            "mobile": "Mobile",
            "kotlin": "Mobile",
            # Desktop Development
            "c#": "Desktop",
            ".net": "Desktop",
            "c++": "Desktop",
            "electron": "Desktop",
            "qt": "Desktop",
            "gtk": "Desktop",
            "winforms": "Desktop",
            "wpf": "Desktop",
            # AI / Machine Learning
            "tensorflow": "AI",
            "pytorch": "AI",
            "jupyter": "AI",
            "numpy": "AI",
            "pandas": "AI",
            "scikit": "AI",
            "machine learning": "AI",
            "ai": "AI",
            "data science": "AI",
            "r": "AI",
            "keras": "AI",
            "opencv": "AI",
            "nlp": "AI",
            # API / Backend
            "rest": "API",
            "api": "API",
            "graphql": "API",
            "spring": "API",
            "java": "API",
            "go": "API",
            "rust": "API",
            # CLI / Terminal
            "cli": "CLI",
            "terminal": "CLI",
            "bash": "CLI",
            "shell": "CLI",
            "zsh": "CLI",
            "powershell": "CLI",
            # IoT / Embedded
            "iot": "IoT",
            "embedded": "IoT",
            "arduino": "IoT",
            "raspberry": "IoT",
            "firmware": "IoT",
            "c": "IoT",
            # Game Development
            "unity": "Game",
            "unreal": "Game",
            "godot": "Game",
            "game": "Game",
            "cocos": "Game",
            # Library / Framework
            "library": "Library",
            "framework": "Library",
            "sdk": "Library",
            "toolkit": "Library",
            # Database
            "sql": "API",
            "postgresql": "API",
            "mysql": "API",
            "mongodb": "API",
            "redis": "API",
            "elasticsearch": "API",
            "database": "API",
            # Security
            "security": "API",
            "penetration": "API",
            "cryptography": "API",
            "pentest": "API",
            "auth": "API",
            "oauth": "API",
            # Python
            "python": "Web",
            # Default / long tail (duplicate keys collapse to one entry each,
            # which is fine since they all map to the same category)
            "perl": "CLI",
            "elixir": "Web",
            "erlang": "Web",
            "haskell": "CLI",
            "scala": "API",
            "clojure": "Web",
            "assembly": "IoT",
            "system": "IoT",
            "lua": "Game",
        }

    def get_category_for_language(self, language):
        """Get category for a given language"""
        if not language:
            return None

        language_lower = language.lower()

        # Check for exact match first
        if language_lower in self.category_map:
            return self.category_map[language_lower]

        # Check for partial matches, longest key first, so specific keys
        # (e.g. "react native") take priority over short, generic ones
        # (e.g. "c", "r", "go") that could otherwise match by accident
        # as a substring of an unrelated language name.
        for key in self._sorted_keys:
            if key in language_lower:
                return self.category_map[key]

        return "Other"

    def calculate_confidence(self, repo, category):
        """Calculate confidence score for categorization"""
        if not repo.primary_language:
            return 50

        # Higher confidence for specific languages
        high_confidence = 95
        medium_confidence = 80
        low_confidence = 65

        # Check if language is a specific match
        language_lower = repo.primary_language.lower()

        # High confidence for clear matches
        if language_lower in [
            "python",
            "javascript",
            "typescript",
            "java",
            "c#",
            "c++",
            "ruby",
            "go",
            "rust",
            "swift",
            "kotlin",
            "php",
            "html",
            "css",
            "react",
            "vue",
            "angular",
            "django",
            "flask",
        ]:
            return high_confidence

        # Medium confidence for framework matches
        if any(
            framework in language_lower
            for framework in [
                "django",
                "flask",
                "react",
                "vue",
                "angular",
                "spring",
                "laravel",
                "rails",
                "unity",
                "unreal",
                "godot",
            ]
        ):
            return medium_confidence

        # Low confidence for others
        return low_confidence

    @transaction.atomic
    def categorize_all_repositories(self):
        """Categorize all repositories"""
        repos = Repository.objects.select_related("user").all()
        count = 0

        for repo in repos:
            category_name = self.get_category_for_language(repo.primary_language)

            if category_name:
                confidence = self.calculate_confidence(repo, category_name)

                # `category` must be part of the lookup (not just `defaults`)
                # to match the model's unique_together = ["repository", "category"].
                # Without it, update_or_create() effectively does
                # .get(repository=repo), which either overwrites an
                # unrelated existing category row for that repo, or raises
                # MultipleObjectsReturned once a repo has more than one
                # category row (e.g. created via the bulk_create endpoint).
                ProjectCategory.objects.update_or_create(
                    repository=repo,
                    category=category_name,
                    defaults={
                        "confidence": confidence,
                    },
                )
                count += 1

        return count
