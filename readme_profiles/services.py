from django.db.models import Sum
from django.utils import timezone
from datetime import timedelta
from repositories.models import Repository
from analytics.models import ContributorActivity


class ReadmeGenerator:
    """Service for generating README content with dynamic data"""

    def __init__(self, user):
        self.user = user
        self.data = {}

    def gather_data(self):
        """Gather all analytics data for the user"""
        try:
            # Basic user info
            self.data["user"] = {
                "name": self.user.display_name or self.user.username,
                "username": self.user.username,
                "bio": self.user.bio or "",
                "location": self.user.location or "",
                "company": self.user.company or "",
                "blog": self.user.blog or "",
                "avatar_url": self.user.avatar_url,
                "followers": self.user.followers or 0,
                "following": self.user.following or 0,
            }
        except Exception as e:
            # Fallback user data
            self.data["user"] = {
                "name": self.user.username,
                "username": self.user.username,
                "bio": "",
                "location": "",
                "company": "",
                "blog": "",
                "avatar_url": "",
                "followers": 0,
                "following": 0,
            }

        try:
            # Repository stats
            repos = Repository.objects.filter(user=self.user)
            total_repos = repos.count()
            total_stars = repos.aggregate(Sum("stars"))["stars__sum"] or 0
            total_forks = repos.aggregate(Sum("forks"))["forks__sum"] or 0

            self.data["stats"] = {
                "total_repos": total_repos,
                "total_stars": total_stars,
                "total_forks": total_forks,
                "public_repos": repos.filter(visibility="public").count(),
                "private_repos": repos.filter(visibility="private").count(),
            }
        except Exception as e:
            # Fallback stats
            self.data["stats"] = {
                "total_repos": 0,
                "total_stars": 0,
                "total_forks": 0,
                "public_repos": 0,
                "private_repos": 0,
            }

        try:
            # Top repositories (most starred)
            repos = Repository.objects.filter(user=self.user).order_by("-stars")[:5]
            self.data["top_repos"] = [
                {
                    "name": repo.name,
                    "full_name": repo.full_name,
                    "description": repo.description or "",
                    "stars": repo.stars or 0,
                    "forks": repo.forks or 0,
                    "language": repo.primary_language or "",
                    "url": repo.homepage or "",
                }
                for repo in repos
            ]
        except Exception as e:
            self.data["top_repos"] = []

        try:
            # Contributions (last 30 days)
            thirty_days_ago = timezone.now() - timedelta(days=30)
            activities = ContributorActivity.objects.filter(
                repository_contributor__repository__user=self.user,
                period_start__gte=thirty_days_ago,
            )

            total_commits = activities.aggregate(Sum("commits"))["commits__sum"] or 0
            total_prs = (
                activities.aggregate(Sum("pull_requests"))["pull_requests__sum"] or 0
            )
            total_issues = activities.aggregate(Sum("issues"))["issues__sum"] or 0

            self.data["contributions"] = {
                "last_30_days": {
                    "commits": total_commits,
                    "pull_requests": total_prs,
                    "issues": total_issues,
                }
            }
        except Exception as e:
            self.data["contributions"] = {
                "last_30_days": {
                    "commits": 0,
                    "pull_requests": 0,
                    "issues": 0,
                }
            }

        # Current date
        self.data["current_date"] = timezone.now().strftime("%B %d, %Y")
        self.data["current_year"] = timezone.now().year

        return self.data

    def replace_placeholders(self, content):
        """Replace placeholders in markdown content with actual data"""
        try:
            data = self.gather_data()
        except Exception as e:
            # If gathering data fails, use empty data
            data = {
                "user": {
                    "name": self.user.username,
                    "username": self.user.username,
                    "bio": "",
                    "location": "",
                    "company": "",
                    "blog": "",
                    "followers": 0,
                    "following": 0,
                },
                "stats": {
                    "total_repos": 0,
                    "total_stars": 0,
                    "total_forks": 0,
                    "public_repos": 0,
                    "private_repos": 0,
                },
                "contributions": {
                    "last_30_days": {
                        "commits": 0,
                        "pull_requests": 0,
                        "issues": 0,
                    }
                },
                "current_date": timezone.now().strftime("%B %d, %Y"),
                "current_year": timezone.now().year,
            }

        # User placeholders
        content = content.replace(
            "{{user.name}}",
            str(
                data["user"].get(
                    "name", data["user"].get("username", self.user.username)
                )
            ),
        )
        content = content.replace(
            "{{user.username}}", str(data["user"].get("username", self.user.username))
        )
        content = content.replace("{{user.bio}}", str(data["user"].get("bio", "")))
        content = content.replace(
            "{{user.location}}", str(data["user"].get("location", ""))
        )
        content = content.replace(
            "{{user.company}}", str(data["user"].get("company", ""))
        )
        content = content.replace("{{user.blog}}", str(data["user"].get("blog", "")))
        content = content.replace(
            "{{user.followers}}", str(data["user"].get("followers", 0))
        )
        content = content.replace(
            "{{user.following}}", str(data["user"].get("following", 0))
        )

        # Stats placeholders
        content = content.replace(
            "{{stats.total_repos}}", str(data["stats"].get("total_repos", 0))
        )
        content = content.replace(
            "{{stats.total_stars}}", str(data["stats"].get("total_stars", 0))
        )
        content = content.replace(
            "{{stats.total_forks}}", str(data["stats"].get("total_forks", 0))
        )
        content = content.replace(
            "{{stats.public_repos}}", str(data["stats"].get("public_repos", 0))
        )
        content = content.replace(
            "{{stats.private_repos}}", str(data["stats"].get("private_repos", 0))
        )

        # Contributions
        contributions = data.get("contributions", {}).get("last_30_days", {})
        content = content.replace(
            "{{contributions.last_30_days.commits}}",
            str(contributions.get("commits", 0)),
        )
        content = content.replace(
            "{{contributions.last_30_days.prs}}",
            str(contributions.get("pull_requests", 0)),
        )
        content = content.replace(
            "{{contributions.last_30_days.issues}}", str(contributions.get("issues", 0))
        )

        # Dates
        content = content.replace(
            "{{current_date}}",
            str(data.get("current_date", timezone.now().strftime("%B %d, %Y"))),
        )
        content = content.replace(
            "{{current_year}}", str(data.get("current_year", timezone.now().year))
        )

        return content

    def generate_badges_section(self):
        """Generate GitHub badges markdown"""
        try:
            data = self.gather_data()
            stats = data.get("stats", {})
            user_data = data.get("user", {})

            badges = []
            badges.append(
                f'![GitHub Repos](https://img.shields.io/badge/Repos-{stats.get("total_repos", 0)}-blue)'
            )
            badges.append(
                f'![GitHub Stars](https://img.shields.io/badge/Stars-{stats.get("total_stars", 0)}-yellow)'
            )
            badges.append(
                f'![GitHub Forks](https://img.shields.io/badge/Forks-{stats.get("total_forks", 0)}-orange)'
            )
            badges.append(
                f'![GitHub Followers](https://img.shields.io/badge/Followers-{user_data.get("followers", 0)}-brightgreen)'
            )

            badges_line = " ".join(badges)
            return f'<div align="center">\n\n{badges_line}\n\n</div>'
        except Exception as e:
            return ""

    def generate_activity_chart(self):
        """Generate GitHub activity chart"""
        try:
            return f'<div align="center">\n\n![GitHub Activity](https://github-profile-summary-cards.vercel.app/api/cards/profile-details?username={self.user.username})\n\n</div>'
        except Exception as e:
            return ""

    def generate_commit_analytics(self):
        """Generate commit analytics section with detailed breakdown"""
        try:
            data = self.gather_data()
            contributions = data.get("contributions", {}).get("last_30_days", {})

            # Get commit activity by week for the last 30 days
            # This would be more detailed if you have per-week commit data

            analytics = f"""
## 📊 Commit Analytics

### Last 30 Days Summary

| Metric | Count |
|---|---|
| Total Commits | {contributions.get('commits', 0)} |
| Pull Requests | {contributions.get('pull_requests', 0)} |
| Issues Created | {contributions.get('issues', 0)} |

### Commit Frequency

- Daily Average: {round(contributions.get('commits', 0) / 30, 1)} commits/day
- PR Average: {round(contributions.get('pull_requests', 0) / 30, 1)} PRs/day

---
"""
            return analytics
        except Exception as e:
            return ""

    def get_user_content(self):
        """Get the user's content from their profile or use default"""
        try:
            from .models import ReadmeProfile

            profile = ReadmeProfile.objects.get(user=self.user)
            return profile.content or self.get_default_template()
        except ReadmeProfile.DoesNotExist:
            return self.get_default_template()
        except Exception as e:
            return self.get_default_template()

    def generate(self, template=None):
        """Generate the final README content"""
        try:
            # Get the template content
            if template:
                content = template
            else:
                content = self.get_user_content()

            # Replace placeholders
            content = self.replace_placeholders(content)

            # Add badges
            badges = self.generate_badges_section()
            if badges:
                content = badges + "\n\n" + content

            # Add commit analytics
            commit_analytics = self.generate_commit_analytics()
            if commit_analytics:
                content += "\n\n" + commit_analytics

            # Add activity chart
            chart = self.generate_activity_chart()
            if chart:
                content += "\n\n" + chart

            return content
        except Exception as e:
            # Return a simple default if everything fails
            return f"""# Hi there, I'm {self.user.username}!

Welcome to my GitHub profile!

*This README was generated automatically. Please check the README Profile settings.*

---
*Last updated: {timezone.now().strftime('%B %d, %Y')}*
"""

    def get_default_template(self):
        """Return a default template with placeholders - No emojis for MySQL compatibility"""
        return """
<div align="center">

# {{user.name}}

{{user.bio}}

**Location:** {{user.location}} &nbsp;|&nbsp; **Company:** {{user.company}} &nbsp;|&nbsp; **Blog:** {{user.blog}}

</div>

---

## GitHub Stats

![GitHub Stats](https://github-readme-stats.vercel.app/api?username={{user.username}}&show_icons=true&hide_title=true&count_private=true)

| Metric | Count |
|---|---|
| Total Repositories | {{stats.total_repos}} |
| Total Stars Received | {{stats.total_stars}} |
| Total Forks | {{stats.total_forks}} |
| Public Repos | {{stats.public_repos}} |
| Private Repos | {{stats.private_repos}} |

## Recent Activity (Last 30 Days)

| Type | Count |
|---|---|
| Commits | {{contributions.last_30_days.commits}} |
| Pull Requests | {{contributions.last_30_days.prs}} |
| Issues | {{contributions.last_30_days.issues}} |

---

<div align="center">

From [{{user.username}}](https://github.com/{{user.username}})

_Last updated: {{current_date}}_

</div>
"""
