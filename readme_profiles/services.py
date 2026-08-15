from django.db.models import Sum
from django.utils import timezone
from django.conf import settings
from datetime import timedelta
import re
from repositories.models import Repository
from analytics.models import ContributorActivity


class ReadmeGenerator:
    """Service for generating README content with dynamic data"""

    DEFAULT_SETTINGS = {
        "show_stats": True,
        "show_languages": True,
        "show_contributions": True,
        "show_activity_chart": True,
        "show_badges": True,
    }

    def __init__(self, user):
        self.user = user
        self.data = {}

    def get_github_username(self):
        """Get the real GitHub login for the user, or None if we don't
        have one on file.

        display_name is a human display name (can contain spaces,
        parentheses, etc., e.g. "EXPN (Exp)") and must NEVER be used as
        a username - it isn't a valid GitHub handle and breaks every
        badge/API URL built from it. Likewise, self.user.username can be
        a synthetic 'github_<id>' placeholder and is never a safe
        fallback either.
        """
        if hasattr(self.user, "github_username") and self.user.github_username:
            if not self.user.github_username.startswith("github_"):
                return self.user.github_username
        return None

    def gather_data(self):
        """Gather all analytics data for the user"""
        github_username = self.get_github_username()

        try:
            # Basic user info
            self.data["user"] = {
                "name": self.user.display_name or github_username or self.user.username,
                "username": github_username,  # may be None - handle downstream
                "bio": self.user.bio or "",
                "location": self.user.location or "",
                "company": self.user.company or "",
                "blog": self.user.blog or "",
                "avatar_url": self.user.avatar_url,
                "followers": self.user.followers or 0,
                "following": self.user.following or 0,
            }
        except Exception:
            # Fallback user data
            self.data["user"] = {
                "name": github_username or self.user.username,
                "username": github_username,
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
        except Exception:
            # Fallback stats
            self.data["stats"] = {
                "total_repos": 0,
                "total_stars": 0,
                "total_forks": 0,
                "public_repos": 0,
                "private_repos": 0,
            }

        try:
            # Top 5 languages
            language_stats = {}
            repos = Repository.objects.filter(user=self.user)
            for repo in repos:
                if repo.primary_language:
                    language_stats[repo.primary_language] = (
                        language_stats.get(repo.primary_language, 0) + 1
                    )

            sorted_languages = sorted(
                language_stats.items(), key=lambda x: x[1], reverse=True
            )[:5]
            self.data["languages"] = [
                {"name": lang, "count": count} for lang, count in sorted_languages
            ]
        except Exception:
            self.data["languages"] = []

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
        except Exception:
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
        except Exception:
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

    def _resolve_settings(self, profile_settings):
        """Merge whatever is stored on the profile with defaults so a
        missing key never silently means 'show everything', and a caller
        that doesn't pass settings at all still gets the old always-on
        behavior (backwards compatible)."""
        resolved = dict(self.DEFAULT_SETTINGS)
        if profile_settings:
            for key in self.DEFAULT_SETTINGS:
                if key in profile_settings:
                    resolved[key] = bool(profile_settings[key])
        return resolved

    def replace_placeholders(self, content, show_settings=None):
        """Replace placeholders in markdown content with actual data"""
        show_settings = show_settings or self.DEFAULT_SETTINGS

        try:
            data = self.gather_data()
        except Exception:
            # If gathering data fails, use empty data
            github_username = self.get_github_username()
            data = {
                "user": {
                    "name": github_username or self.user.username,
                    "username": github_username,
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
                "languages": [],
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

        # Fall back to a safe, non-None display value for the username
        # placeholder so we never render the literal string "None" into
        # the markdown or a broken github.com/None link.
        display_username = data["user"].get("username") or self.user.username

        # User placeholders
        content = content.replace(
            "{{user.name}}",
            str(data["user"].get("name", display_username)),
        )
        content = content.replace("{{user.username}}", str(display_username))
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

        # Languages - honor show_languages
        if show_settings.get("show_languages", True):
            languages = data.get("languages", [])
            if languages:
                lang_string = ", ".join(
                    [f"{lang['name']} ({lang['count']} repos)" for lang in languages]
                )
                content = content.replace("{{languages.top_5}}", lang_string)
            else:
                content = content.replace(
                    "{{languages.top_5}}", "No languages detected"
                )
        else:
            content = self._strip_placeholder_block(content, "{{languages.top_5}}")

        # Contributions - honor show_contributions
        if show_settings.get("show_contributions", True):
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
                "{{contributions.last_30_days.issues}}",
                str(contributions.get("issues", 0)),
            )
        else:
            for placeholder in (
                "{{contributions.last_30_days.commits}}",
                "{{contributions.last_30_days.prs}}",
                "{{contributions.last_30_days.issues}}",
            ):
                content = self._strip_placeholder_block(content, placeholder)

        # Dates
        content = content.replace(
            "{{current_date}}",
            str(data.get("current_date", timezone.now().strftime("%B %d, %Y"))),
        )
        content = content.replace(
            "{{current_year}}", str(data.get("current_year", timezone.now().year))
        )

        # Stats card image - our own self-hosted SVG, not a third-party service
        username = self.get_github_username()
        if show_settings.get("show_stats", True) and username:
            base_url = getattr(
                settings, "SITE_URL", "https://gitstats-api-1i3g.onrender.com"
            )
            stats_card_url = (
                f"{base_url}/api/readme-profile/readme-card/stats/?username={username}"
            )
            content = content.replace("{{stats_card_url}}", stats_card_url)
        else:
            stats_card_url = None
            # Either stats are turned off, or no valid username - drop the
            # whole image line rather than rendering a broken/empty src.
            content = re.sub(r"!\[[^\]]*\]\(\{\{stats_card_url\}\}\)\n?", "", content)

        # Also normalize/strip any stats card image that's already baked
        # into content from a prior generation (the {{stats_card_url}}
        # token above won't exist anymore once content has been
        # generated once, so that replace() alone is a no-op on it).
        content = self._normalize_stats_card_image(content, stats_card_url)

        return content

    @staticmethod
    def _strip_previous_badges(content):
        """Remove any badges block already baked into content from a
        prior generation. Without this, calling generate() again on
        already-generated content (which is what happens today, since
        regenerate() saves the resolved output back into profile.content)
        prepends a second badges block on top of the first, and a third
        on the next regenerate, etc."""
        pattern = re.compile(
            r'<div align="center">\s*\n\n[^\n<]*img\.shields\.io/badge/Repos-[^\n<]*\n\n</div>\s*\n*',
            re.DOTALL,
        )
        return pattern.sub("", content)

    @staticmethod
    def _strip_previous_activity_chart(content):
        """Same idea as _strip_previous_badges, but for the appended
        'Top Languages' image chart. Also cleans up stale copies left
        over from before the /api/readme-profile/ URL prefix fix, since
        those won't match the freshly-built URL and would otherwise
        linger alongside the corrected one forever."""
        pattern = re.compile(
            r'<div align="center">\s*\n\n!\[Top Languages\]\([^)]*\)\s*\n\n</div>\s*\n*',
            re.DOTALL,
        )
        return pattern.sub("", content)

    @staticmethod
    def _normalize_stats_card_image(content, new_url):
        """Fix up an already-baked '![GitHub Stats](...)' line in stored
        content to point at the current, correct URL - or strip it if
        stats are disabled / there's no username. Needed because once
        content has been generated once, {{stats_card_url}} no longer
        exists in it for replace_placeholders() to substitute into."""
        pattern = re.compile(r"!\[GitHub Stats\]\([^)]*\)")
        if new_url:
            return pattern.sub(f"![GitHub Stats]({new_url})", content)
        return pattern.sub("", content)

    @staticmethod
    def _strip_placeholder_block(content, placeholder):
        """When a section is toggled off, drop the line containing its
        placeholder entirely rather than leaving a dangling label with
        nothing after it (e.g. a table row with an empty cell)."""
        lines = content.split("\n")
        kept = [line for line in lines if placeholder not in line]
        return "\n".join(kept)

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
        except Exception:
            return ""

    def generate_activity_chart(self):
        """Embed our own languages card instead of a third-party image
        service - built from the same data we already have, served from
        our own domain, no external lookups that can 404."""
        username = self.get_github_username()
        if not username:
            return ""
        base_url = getattr(
            settings, "SITE_URL", "https://gitstats-api-1i3g.onrender.com"
        )
        return f'<div align="center">\n\n![Top Languages]({base_url}/api/readme-profile/readme-card/languages/?username={username})\n\n</div>'

    def get_user_content(self):
        """Get the user's content from their profile or use default"""
        try:
            from .models import ReadmeProfile

            profile = ReadmeProfile.objects.get(user=self.user)
            return profile.content or self.get_default_template()
        except ReadmeProfile.DoesNotExist:
            return self.get_default_template()
        except Exception:
            return self.get_default_template()

    def _strip_broken_github_images(self, content):
        """Remove any github-readme-stats / github-profile-summary-cards
        image embeds from content. These build their URL from a GitHub
        username - if we don't have a real one, the URL contains a fake
        placeholder and 404s with "could not find that user or
        organization" instead of just not rendering. Better to omit the
        image than show a broken error card."""
        pattern = re.compile(
            r"!\[[^\]]*\]\("
            r"https://(?:github-readme-stats\.vercel\.app|"
            r"github-profile-summary-cards\.vercel\.app)[^)]*\)"
        )
        return pattern.sub("", content)

    def generate(self, template=None, profile_settings=None):
        """Generate the final README content.

        profile_settings should be the dict stored on ReadmeProfile.settings
        (show_stats / show_languages / show_contributions /
        show_activity_chart / show_badges). Any key not present defaults to
        True so existing profiles created before these toggles existed keep
        their current behavior.
        """
        show_settings = self._resolve_settings(profile_settings)

        try:
            # Get the template content
            if template:
                content = template
            else:
                content = self.get_user_content()

            # Replace placeholders (this now also honors show_stats /
            # show_languages / show_contributions and strips the
            # corresponding lines when turned off)
            content = self.replace_placeholders(content, show_settings)

            # Strip any badges/chart blocks already baked in from a prior
            # generation before re-adding fresh ones below, so repeated
            # regenerate() calls don't keep stacking duplicates.
            content = self._strip_previous_badges(content)
            content = self._strip_previous_activity_chart(content)

            # If there's no real GitHub username on file, any stats/chart
            # image embedded in the template body would otherwise render
            # with a fake placeholder username and show a broken "could
            # not find that user or organization" error card.
            if not self.get_github_username():
                content = self._strip_broken_github_images(content)

            # Add badges - honor show_badges
            if show_settings.get("show_badges", True):
                badges = self.generate_badges_section()
                if badges:
                    content = badges + "\n\n" + content

            # Add activity chart - honor show_activity_chart. This was
            # previously appended unconditionally, which is why disabling
            # it in profile settings never actually removed it, and why
            # it duplicated the plain-text {{languages.top_5}} list that's
            # already in the default template body.
            if show_settings.get("show_activity_chart", True):
                chart = self.generate_activity_chart()
                if chart:
                    content += "\n\n" + chart

            return content
        except Exception:
            # Return a simple default if everything fails
            name = self.get_github_username() or self.user.username
            return f"""# Hi there, I'm {name}!

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

![GitHub Stats]({{stats_card_url}})

### Activity Summary

| Metric | Count |
|---|---|
| Total Repositories | {{stats.total_repos}} |
| Total Stars Received | {{stats.total_stars}} |
| Total Forks | {{stats.total_forks}} |
| Public Repos | {{stats.public_repos}} |
| Private Repos | {{stats.private_repos}} |

### Top Languages

{{languages.top_5}}

### Recent Activity (Last 30 Days)

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
