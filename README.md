# GitStats — GitHub Stats & README Profile Generator API

> Tired of manually keeping your GitHub profile and README up to date? **GitStats** is a powerful Django REST API that connects to your GitHub account, continuously tracks your repositories, stars, forks, contributions, and languages, and can even auto-generate a beautiful, always-fresh **GitHub profile README** for you.

GitStats is the backend engine for a full-stack GitHub statistics dashboard. It authenticates users securely through GitHub (via Firebase Identity + server-side token exchange), syncs their repositories along with detailed statistics and contributor data, and exposes a clean, feature-rich REST API that front-ends consume to display dashboards, charts, leaderboards, and community features.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
  - [Secure GitHub Authentication](#1-secure-github-authentication)
  - [Repository Management & Sync](#2-repository-management--sync)
  - [Statistics & Analytics Engine](#3-statistics--analytics-engine)
  - [Programming Language Insights](#4-programming-language-insights)
  - [Automatic Project Categorization](#5-automatic-project-categorization)
  - [README Profile Generator](#6-readme-profile-generator)
  - [Communities & Posts](#7-communities--posts)
  - [Automated Background Sync](#8-automated-background-sync)
- [Tech Stack](#tech-stack)
- [API Overview](#api-overview)
- [Getting Started](#getting-started)
- [Deployment](#deployment)

---

## Overview

GitStats is a **GitHub statistics synchronizer and analytics API**. After a user signs in with GitHub, the API:

1. Retrieves their GitHub profile information, avatar, bio, location, followers, and follower counts.
2. Syncs repositories (public and private), including stars, forks, watchers, open issues, language, visibility, and license data.
3. Collects historical statistics over time so charts and trends can be plotted.
4. Fetches and stores contributor and contributor activity data (commits, pull requests, reviews, issues, additions/deletions).
5. Auto-categorizes every repository into categories like **Web**, **Mobile**, **AI**, **API**, **CLI**, **IoT**, **Game** and more, complete with confidence scores.
6. Generates — and optionally **auto-updates on a schedule** — a personalized GitHub profile README filled with live stats, badges, language breakdowns, and activity charts.

The project is structured as a multi-tenant API where every user sees and controls only their own data, making it both a personal tool and a scalable multi-user platform.

---

## Key Features

### 1. Secure GitHub Authentication

- **Firebase + GitHub login** — users authenticate through Firebase using their GitHub account; the API verifies the ID token, validates the provider, and creates/updates the local user automatically.
- **Server-side GitHub OAuth exchange** (`/api/users/auth/github/exchange/`) — the GitHub access code is exchanged for an access token on the server so the **client secret never touches the browser**.
- **Automatic profile enrichment** — when your data is retrieved, the API automatically retains your name, avatar, bio, location, company, blog, followers, following, and public repository counts from the GitHub API.
- **Add/Remove GitHub tokens** — connect a token later or revoke it at any time.
- **User search API** — find other users by name, username, or email to build social features.

### 2. Repository Management & Sync

- **Full repository CRUD** — create, read, update, and delete repositories tied to your GitHub account.
- **Rich repository data** — stars, forks, watchers, open issues, size, default branch, primary language, visibility (public/private), license, homepage, archived/disabled flags, and GitHub timestamps.
- **Advanced filtering, search & sorting** — filter by visibility, archived state, or language; search by name; sort by stars, forks, name, or update date.
- **Bulk sync endpoint** (`/repositories/bulk/`) — one request imports or updates an entire repository from GitHub, returning created/updated/error counts.
- **Repository-level user commits** — returns your recent commits for any repo, stored during sync (no live GitHub rate limit usage on every dashboard load).

### 3. Statistics & Analytics Engine

- **Repository stats snapshots** — automatic time-based snapshots of stars, forks, watchers, open issues, subscribers, network, size, and default branch, so you can chart **growth over time**.
- **User-level stats** — aggregate followers, following, total/public/private repos, total stars and forks, with trend tracking.
- **Trend endpoints** (e.g. `/analytics/repository-stats/{id}/trend/`) to plot a repo's stats history in chronological order.
- **Summary analytics** per user — total repositories and stars, total forks, most-starred / most-forked repos, language distribution, and last-updated timestamp.
- **Update logging** — every sync operation (manual, scheduled, webhook, or initial) is recorded with status (PENDING → IN_PROGRESS → SUCCESS/FAILED), how many repos were updated, error messages, and timestamps.

### 4. Language Insights

- **Per-repository language tracking** — each repository stores its languages, with byte counts and percentage breakdown.
- **Repository language summaries** — aggregate statistics across repos: total bytes, number of repos, average percentage.
- **Global top languages** — see the most popular languages across the platform and search any language to discover which repos use it.
- **Bulk create/update** — sync an entire repo's language breakdown in one request.
- **Cleanup utility** — automatically removes language entries with under 1% share or zero bytes to keep data tidy.

### 5. Automatic Project Categorization

- **Intelligent auto-tiering** — each repository is assigned a project category (**Web, Mobile, Desktop, AI, API, CLI, IoT, Game, Library, Other**) based on its primary language/tech stack through a built-in rule engine.
- **Confidence scores** — each classification is stored with a confidence score (0–100); exact tech matches get high confidence, framework matches get medium, and general language matches get lower.
- **One-click re-sync** — the `/project-categories/sync/` endpoint re-categorizes every repository in one operation.
- **Category statistics** — counts of projects per category, average/min/max confidence, and per-repository categorization views.

### 6. README & Profile Generator

The showcase feature: **auto-generate a professional GitHub profile README**.

- **Template engine with dynamic placeholders** — content supports mustache-style placeholders like `{{user.name}}`, `{{user.bio}}`, `{{stats.total_stars}}`, `{{stats.total_repos}}`, `{{stats.total_forks}}`, `{{languages.top_5}}`, and `{{contributions.last_30_days.commits}}`, which are filled with live data at generation time.
- **Multiple themes** — choose from Modern, Minimal, Dark Theme, Visual Heavy, and Professional templates (with an extensible `ReadmeTemplate` model for more).
- **Live GitHub stat cards** — automatically embeds `github-readme-stats` cards, a **GitHub activity summary chart**, and shield.io badges for Repos / Stars / Forks / Followers.
- **Customizable content** — set exactly which sections appear (stats, languages, contributions, activity chart, badges), accent color, and your own Markdown body.
- **One-file export** — download the finished Markdown as a ready-to-paste `README_{username}.md` file straight from the API.
- **Generation history** — keeps the last 20 generation events (success/failure, error messages, and content length) for the user to review.

### 7. Communities & Posts

- **Developer communities** — create and discover communities with names, slugs, descriptions, cover images, icons, and a primary programming language.
- **Role-based membership** — members can hold **Owner**, **Moderator**, or **Member** roles; the first member automatically becomes the Owner.
- **Permission-aware updates** — only Owners/Moderators can edit or delete a community or manage members; Owners can promote/demote/remove members.
- **Community posts** — members can share text, GitHub repository links, or blog links within a community; only the author (or community moderators) can edit or delete a post.
- **Filtering & discovery** — browse posts by community or by user, look up communities by slug, and list all communities a user belongs to.

### 8. Automated Background Sync

- **Celery task queue** — a shared task iterates all README profiles due for an update, and individual per-profile tasks generate fresh content and log the outcome.
- **Scheduled auto-updates** — each user chooses daily, weekly, or monthly automated re-generation; the profile records the next update (`auto_update_enabled` + `next_update`).
- **Graceful fallbacks** — if data gathering fails, the generator still produces a clean default README so users are never left with a broken profile.
- **Management commands** — `fetch_contributors` pulls live contributor + language data from the GitHub API; `seed_contributors` generates realistic fake data for testing.

---

## Tech Stack

| Layer        | Technology |
|--------------|------------|
| **Backend**  | Django 5.1, Django REST Framework |
| **Auth**     | Firebase Admin SDK, django-allauth (GitHub provider), token authentication |
| **Database** | MySQL (development), PostgreSQL via Neon (production, `dj_database_url` + SSL) |
| **Task Queue** | Celery |
| **Static hosting** | WhiteNoise (`CompressedManifestStaticFilesStorage`) |
| **CORS**     | `django-cors-headers` (localhost + Netlify deployment) |
| **Deployment** | Gunicorn, `build.sh` build pipeline (pip install → collectstatic → migrate) |

---

## API Overview

| Area | Endpoints (prefix) | Purpose |
|------|-------------------|---------|
| **Users & Auth** | `/api/users/…` | Firebase login, GitHub token exchange, profile info, logout, user search |
| **Repos**        | `/api/repositories/` | Repo CRUD, bulk sync, stats summary, languages, per-user commits |
| **Analytics**    | `/api/analytics/` | Repository stats, user stats, update logs, contributors, advanced activity analytics |
| **Languages**    | `/api/languages/` | Per-repo language breakdown, summaries, top-list, search, cleanup |
| **Categories**   | `/api/project-categories/` | Auto-categorization, stats, bulk create |
| **Communities**  | `/api/communities/` | Community CRUD, members (roles/permissions), joins |
| **Posts**        | `/api/posts/` | Posts within communities, by community/user |
| **README**       | `/api/readme-profile/` | Generate, preview, export, regenerate, auto-update toggle, templates, history |

---

## Getting Started

1. **Clone the repository** and create a virtual environment (`.venv`).
2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables** (`.env`) — `GITHUB_CLIENT_ID`, `GITHUB_CLIENT_SECRET`, `FIREBASE_CREDENTIALS_JSON`, and optionally `DATABASE_URL` for production, plus DB settings.

4. **Run migrations and start the server**:

   ```bash
   python manage.py migrate
   python manage.py runserver
   ```

5. **Start Celery** (for auto-update tasks):

   ```bash
   celery -A config worker -l info --beat
   ```

> The Django admin (`/admin/`) provides full management over repositories, analytics, contributors, communities, and README templates.

---

## Deployment

Production is designed for hosts like **Render** using the provided `build.sh`:

```bash
pip install --upgrade pip
pip install -r requirements.txt
python manage.py collectstatic --no-input
python manage.py migrate
```

Environment variables control DEBUG, allowed hosts, CORS, the database URL, and OAuth secrets — the same codebase runs locally and in production.