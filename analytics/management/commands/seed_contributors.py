import random
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from analytics.models import Contributor, ContributorLanguages
from repositories.models import Repository

User = get_user_model()


class Command(BaseCommand):
    help = "Seed fake contributor data for testing"

    def add_arguments(self, parser):
        parser.add_argument("--user", type=str, help="Username to seed data for")
        parser.add_argument(
            "--count",
            type=int,
            default=10,
            help="Number of contributors per repository (default: 10)",
        )

    def handle(self, *args, **options):
        username = options.get("user")
        count = options.get("count")

        if username:
            users = User.objects.filter(username=username)
        else:
            users = User.objects.all()

        languages = [
            "Python",
            "JavaScript",
            "TypeScript",
            "Java",
            "Go",
            "Rust",
            "Ruby",
            "PHP",
            "C++",
            "C#",
            "HTML",
            "CSS",
            "Shell",
        ]

        for user in users:
            self.stdout.write(f"Seeding contributors for {user.username}")

            repos = Repository.objects.filter(user=user)

            for repo in repos:
                self.stdout.write(
                    f"  Seeding {count} contributors for {repo.full_name}"
                )

                # Clear existing contributors
                Contributor.objects.filter(repository=repo).delete()

                for i in range(count):
                    login = f"contributor_{i+1}"

                    contributor = Contributor.objects.create(
                        user=user,
                        repository=repo,
                        github_id=1000000 + i,
                        login=login,
                        avatar_url=f"https://ui-avatars.com/api/?name={login}&background=6C63FF&color=fff&size=128",
                        html_url=f"https://github.com/{login}",
                        contributions=random.randint(1, 100),
                    )

                    # Add random languages
                    num_languages = random.randint(1, 4)
                    selected_languages = random.sample(languages, num_languages)
                    total_bytes = sum(
                        random.randint(1000, 50000) for _ in range(num_languages)
                    )

                    for lang in selected_languages:
                        bytes_count = random.randint(1000, 50000)
                        percentage = (
                            (bytes_count / total_bytes) * 100 if total_bytes > 0 else 0
                        )

                        ContributorLanguages.objects.create(
                            contributor=contributor,
                            language=lang,
                            bytes=bytes_count,
                            percentage=round(percentage, 2),
                        )

                self.stdout.write(
                    f"    Created {count} contributors with languages for {repo.full_name}"
                )
