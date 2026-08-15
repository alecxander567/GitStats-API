"""
Self-hosted SVG cards for README embeds.

These replace the third-party github-readme-stats.vercel.app /
github-profile-summary-cards.vercel.app images. Since we already compute
all the same data in ReadmeGenerator.gather_data(), we just render it as
SVG ourselves - no external dependency, no "could not find that user or
organization" failures, full control over the design.

Public, unauthenticated GET endpoints: GitHub (and anyone else viewing
the rendered README) needs to be able to load these as plain <img> URLs,
the same way the old vercel ones worked without auth headers.
"""

from django.http import HttpResponse
from django.views import View
from django.db.models import Sum
from users.models import User
from repositories.models import Repository

# Card colors - dark theme, tweak freely
BG_COLOR = "#0d1117"
BORDER_COLOR = "#30363d"
TITLE_COLOR = "#58a6ff"
TEXT_COLOR = "#c9d1d9"
MUTED_COLOR = "#8b949e"
ACCENT_COLORS = [
    "#58a6ff",  # blue
    "#3fb950",  # green
    "#f0883e",  # orange
    "#a371f7",  # purple
    "#f778ba",  # pink
]


def _escape(text):
    """Minimal XML escaping for text nodes."""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _get_user_by_identifier(identifier):
    """Look up a user by github_username first (the real handle),
    falling back to internal username for backwards compatibility."""
    user = User.objects.filter(github_username=identifier).first()
    if user:
        return user
    return User.objects.filter(username=identifier).first()


def build_stats_svg(user):
    """Repo / star / fork / follower / public-private breakdown card."""
    repos = Repository.objects.filter(user=user)
    total_repos = repos.count()
    total_stars = repos.aggregate(Sum("stars"))["stars__sum"] or 0
    total_forks = repos.aggregate(Sum("forks"))["forks__sum"] or 0
    public_repos = repos.filter(visibility="public").count()
    private_repos = repos.filter(visibility="private").count()

    display_name = _escape(user.display_name or user.github_username or user.username)

    rows = [
        ("Total Repositories", total_repos),
        ("Total Stars", total_stars),
        ("Total Forks", total_forks),
        ("Public Repos", public_repos),
        ("Private Repos", private_repos),
        ("Followers", user.followers or 0),
    ]

    width = 420
    row_height = 30
    header_height = 50
    padding = 20
    height = header_height + len(rows) * row_height + padding

    row_svgs = []
    for i, (label, value) in enumerate(rows):
        y = header_height + i * row_height + 20
        row_svgs.append(f"""
        <text x="{padding}" y="{y}" font-family="'Segoe UI', Ubuntu, sans-serif"
              font-size="14" fill="{TEXT_COLOR}">{_escape(label)}</text>
        <text x="{width - padding}" y="{y}" font-family="'Segoe UI', Ubuntu, sans-serif"
              font-size="14" font-weight="bold" fill="{TITLE_COLOR}" text-anchor="end">{value}</text>
        """)

    svg = f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}"
     xmlns="http://www.w3.org/2000/svg" role="img" aria-label="GitHub stats for {display_name}">
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12"
        fill="{BG_COLOR}" stroke="{BORDER_COLOR}" stroke-width="1"/>
  <text x="{padding}" y="32" font-family="'Segoe UI', Ubuntu, sans-serif"
        font-size="18" font-weight="bold" fill="{TITLE_COLOR}">{display_name}'s GitHub Stats</text>
  {''.join(row_svgs)}
</svg>"""
    return svg


def build_languages_svg(user):
    """Top-5 language breakdown as horizontal bars."""
    repos = Repository.objects.filter(user=user)
    language_counts = {}
    for repo in repos:
        if repo.primary_language:
            language_counts[repo.primary_language] = (
                language_counts.get(repo.primary_language, 0) + 1
            )

    sorted_languages = sorted(
        language_counts.items(), key=lambda x: x[1], reverse=True
    )[:5]

    width = 420
    row_height = 40
    header_height = 50
    padding = 20
    height = header_height + max(len(sorted_languages), 1) * row_height + padding

    if not sorted_languages:
        bars_svg = f"""
        <text x="{padding}" y="{header_height + 25}" font-family="'Segoe UI', Ubuntu, sans-serif"
              font-size="14" fill="{MUTED_COLOR}">No languages detected</text>
        """
    else:
        max_count = sorted_languages[0][1]
        bar_max_width = width - padding * 2 - 90
        bars = []
        for i, (lang, count) in enumerate(sorted_languages):
            y = header_height + i * row_height
            bar_width = max(int((count / max_count) * bar_max_width), 4)
            color = ACCENT_COLORS[i % len(ACCENT_COLORS)]
            bars.append(f"""
            <text x="{padding}" y="{y + 15}" font-family="'Segoe UI', Ubuntu, sans-serif"
                  font-size="13" fill="{TEXT_COLOR}">{_escape(lang)}</text>
            <rect x="{padding}" y="{y + 22}" width="{bar_max_width}" height="8" rx="4"
                  fill="{BORDER_COLOR}"/>
            <rect x="{padding}" y="{y + 22}" width="{bar_width}" height="8" rx="4"
                  fill="{color}"/>
            <text x="{width - padding}" y="{y + 15}" font-family="'Segoe UI', Ubuntu, sans-serif"
                  font-size="13" fill="{MUTED_COLOR}" text-anchor="end">{count} repos</text>
            """)
        bars_svg = "".join(bars)

    svg = f"""<svg width="{width}" height="{height}" viewBox="0 0 {width} {height}"
     xmlns="http://www.w3.org/2000/svg" role="img" aria-label="Top languages">
  <rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="12"
        fill="{BG_COLOR}" stroke="{BORDER_COLOR}" stroke-width="1"/>
  <text x="{padding}" y="32" font-family="'Segoe UI', Ubuntu, sans-serif"
        font-size="18" font-weight="bold" fill="{TITLE_COLOR}">Most Used Languages</text>
  {bars_svg}
</svg>"""
    return svg


class ReadmeStatsCardView(View):
    """GET /api/readme-card/stats/?username=<github_username>"""

    def get(self, request):
        username = request.GET.get("username")
        if not username:
            return HttpResponse("username is required", status=400)

        user = _get_user_by_identifier(username)
        if not user:
            return HttpResponse("user not found", status=404)

        svg = build_stats_svg(user)
        response = HttpResponse(svg, content_type="image/svg+xml")
        # Cache for 10 minutes - avoids hammering the DB on every README view
        response["Cache-Control"] = "public, max-age=600"
        return response


class ReadmeLanguagesCardView(View):
    """GET /api/readme-card/languages/?username=<github_username>"""

    def get(self, request):
        username = request.GET.get("username")
        if not username:
            return HttpResponse("username is required", status=400)

        user = _get_user_by_identifier(username)
        if not user:
            return HttpResponse("user not found", status=404)

        svg = build_languages_svg(user)
        response = HttpResponse(svg, content_type="image/svg+xml")
        response["Cache-Control"] = "public, max-age=600"
        return response
