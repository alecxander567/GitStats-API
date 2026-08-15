from .models import ProjectCategory
from repositories.models import Repository
from django.contrib.auth import get_user_model
from django.db import transaction

User = get_user_model()


class CategoryService:
    """Service for categorizing repositories"""

    def __init__(self):
        self.category_map = self._get_category_map()

    def _get_category_map(self):
        """Get the mapping of languages to categories"""
        return {
            # Web Development - Frontend
            "html": "Web Development",
            "css": "Web Development",
            "javascript": "Web Development",
            "typescript": "Web Development",
            "react": "Web Development",
            "vue": "Web Development",
            "angular": "Web Development",
            "svelte": "Web Development",
            "nextjs": "Web Development",
            "nuxt": "Web Development",
            "tailwind": "Web Development",
            "bootstrap": "Web Development",
            # Web Development - Backend
            "python": "Backend Development",
            "django": "Backend Development",
            "flask": "Backend Development",
            "fastapi": "Backend Development",
            "node": "Backend Development",
            "express": "Backend Development",
            "java": "Backend Development",
            "spring": "Backend Development",
            "c#": "Backend Development",
            ".net": "Backend Development",
            "php": "Backend Development",
            "laravel": "Backend Development",
            "ruby": "Backend Development",
            "rails": "Backend Development",
            "go": "Backend Development",
            "rust": "Backend Development",
            "kotlin": "Backend Development",
            # Mobile Development
            "swift": "Mobile Development",
            "flutter": "Mobile Development",
            "react native": "Mobile Development",
            "android": "Mobile Development",
            "ios": "Mobile Development",
            "mobile": "Mobile Development",
            # Data Science & AI
            "data science": "Data Science & AI",
            "machine learning": "Data Science & AI",
            "ai": "Data Science & AI",
            "tensorflow": "Data Science & AI",
            "pytorch": "Data Science & AI",
            "jupyter": "Data Science & AI",
            "r": "Data Science & AI",
            "numpy": "Data Science & AI",
            "pandas": "Data Science & AI",
            "scikit": "Data Science & AI",
            # DevOps & Infrastructure
            "docker": "DevOps & Infrastructure",
            "kubernetes": "DevOps & Infrastructure",
            "terraform": "DevOps & Infrastructure",
            "ansible": "DevOps & Infrastructure",
            "jenkins": "DevOps & Infrastructure",
            "github actions": "DevOps & Infrastructure",
            "aws": "DevOps & Infrastructure",
            "azure": "DevOps & Infrastructure",
            "gcp": "DevOps & Infrastructure",
            "devops": "DevOps & Infrastructure",
            # Game Development
            "unity": "Game Development",
            "unreal": "Game Development",
            "c++": "Game Development",
            "godot": "Game Development",
            "game": "Game Development",
            # Database
            "sql": "Database",
            "postgresql": "Database",
            "mysql": "Database",
            "mongodb": "Database",
            "redis": "Database",
            "elasticsearch": "Database",
            "database": "Database",
            # Security
            "security": "Security",
            "penetration": "Security",
            "cryptography": "Security",
            "pentest": "Security",
            # Other
            "c": "System Programming",
            "assembly": "System Programming",
            "system": "System Programming",
            "perl": "Scripting",
            "bash": "Scripting",
            "shell": "Scripting",
            "lua": "Scripting",
            "elixir": "Functional Programming",
            "erlang": "Functional Programming",
            "haskell": "Functional Programming",
            "scala": "Functional Programming",
            "clojure": "Functional Programming",
        }

    def get_category_for_language(self, language):
        """Get category for a given language"""
        if not language:
            return None

        language_lower = language.lower()

        # Check for exact match first
        if language_lower in self.category_map:
            return self.category_map[language_lower]

        # Check for partial matches
        for key, category in self.category_map.items():
            if key in language_lower:
                return category

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

                # Only save the fields that exist in the model
                ProjectCategory.objects.update_or_create(
                    repository=repo,
                    defaults={
                        "category": category_name,
                        "confidence": confidence,
                    },
                )
                count += 1

        return count
