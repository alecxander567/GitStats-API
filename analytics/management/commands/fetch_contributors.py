import requests
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from repositories.models import Repository
from analytics.models import Contributor, ContributorLanguages

User = get_user_model()


class Command(BaseCommand):
    help = "Fetch contributors and their languages from GitHub"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user", type=str, help="Username to fetch contributors for (optional)"
        )
        parser.add_argument(
            "--repo",
            type=str,
            help="Repository full_name to fetch contributors for (optional)",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Maximum number of contributors to fetch per repo (default: 100)",
        )

    def handle(self, *args, **options):
        username = options.get("user")
        repo_name = options.get("repo")
        limit = options.get("limit")

        # Get users
        if username:
            users = User.objects.filter(username=username)
        else:
            users = User.objects.all()

        for user in users:
            self.stdout.write(f"Fetching contributors for {user.username}")

            # Get user's repositories
            repos = Repository.objects.filter(user=user)
            if repo_name:
                repos = repos.filter(full_name=repo_name)

            if not repos.exists():
                self.stdout.write(f"  No repositories found for {user.username}")
                continue

            for repo in repos:
                self.fetch_repo_contributors(user, repo, limit)

    def fetch_repo_contributors(self, user, repo, limit):
        """Fetch contributors for a single repository"""
        self.stdout.write(f"  Fetching contributors for {repo.full_name}")

        # Get GitHub token from user's social account
        try:
            from allauth.socialaccount.models import SocialToken, SocialAccount

            social_account = SocialAccount.objects.get(user=user, provider="github")
            token = SocialToken.objects.get(account=social_account)
            github_token = token.token
        except (SocialAccount.DoesNotExist, SocialToken.DoesNotExist):
            self.stdout.write(f"    No GitHub token found for {user.username}")
            return

        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
        }

        # Fetch contributors
        url = f"https://api.github.com/repos/{repo.full_name}/contributors"
        params = {"per_page": limit}

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            contributors_data = response.json()

            if not contributors_data:
                self.stdout.write(f"    No contributors found for {repo.full_name}")
                return

            self.stdout.write(f"    Found {len(contributors_data)} contributors")

            for contributor_data in contributors_data:
                self.process_contributor(user, repo, contributor_data, github_token)

        except requests.exceptions.RequestException as e:
            self.stdout.write(f"    Error fetching contributors: {e}")

    def process_contributor(self, user, repo, contributor_data, github_token):
        """Process a single contributor and their languages"""
        github_id = contributor_data.get("id")
        login = contributor_data.get("login")

        if not github_id or not login:
            return

        # Get or create contributor
        contributor, created = Contributor.objects.get_or_create(
            repository=repo,
            github_id=github_id,
            defaults={
                "user": user,
                "login": login,
                "avatar_url": contributor_data.get("avatar_url", ""),
                "html_url": contributor_data.get("html_url", ""),
                "contributions": contributor_data.get("contributions", 0),
            },
        )

        if not created:
            # Update existing contributor
            contributor.login = login
            contributor.avatar_url = contributor_data.get(
                "avatar_url", contributor.avatar_url
            )
            contributor.html_url = contributor_data.get(
                "html_url", contributor.html_url
            )
            contributor.contributions = contributor_data.get(
                "contributions", contributor.contributions
            )
            contributor.save()

        # Fetch contributor's languages from their repos
        self.fetch_contributor_languages(user, contributor, github_token)

    def fetch_contributor_languages(self, user, contributor, github_token):
        """Fetch languages for a contributor"""
        headers = {
            "Authorization": f"token {github_token}",
            "Accept": "application/vnd.github.v3+json",
        }

        # Get the contributor's repositories
        url = f"https://api.github.com/users/{contributor.login}/repos"
        params = {"per_page": 100, "sort": "updated"}

        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            repos_data = response.json()

            # Collect language data
            language_data = {}

            for repo_data in repos_data:
                # Get languages for each repo
                repo_url = (
                    f"https://api.github.com/repos/{repo_data['full_name']}/languages"
                )
                try:
                    lang_response = requests.get(repo_url, headers=headers)
                    lang_response.raise_for_status()
                    repo_languages = lang_response.json()

                    for lang, bytes_count in repo_languages.items():
                        if lang in language_data:
                            language_data[lang] += bytes_count
                        else:
                            language_data[lang] = bytes_count

                except requests.exceptions.RequestException as e:
                    # Skip if we can't fetch languages for a repo
                    continue

            if language_data:
                total_bytes = sum(language_data.values())

                # Clear existing languages
                contributor.languages.all().delete()

                # Create new language entries
                for lang, bytes_count in language_data.items():
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
                    f"      Added {len(language_data)} languages for {contributor.login}"
                )

        except requests.exceptions.RequestException as e:
            self.stdout.write(f"    Error fetching repos for {contributor.login}: {e}")
