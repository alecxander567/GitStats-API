from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Sum, Count, Avg, Q, F, ExpressionWrapper, FloatField
from django.utils import timezone
from datetime import timedelta
from .models import (
    RepositoryStats,
    UserStats,
    UpdateLog,
    Contributor,
    ContributorLanguages,
    ContributorActivity,
)
from .serializers import (
    RepositoryStatsSerializer,
    UserStatsSerializer,
    UpdateLogSerializer,
    StatsSummarySerializer,
    BulkStatsSerializer,
    ContributorSerializer,
    ContributorBulkCreateSerializer,
    ContributorLanguagesSerializer,
    ContributorActivitySerializer,
    ContributorActivityListSerializer,
    ContributorActivityBulkCreateSerializer,
)
from repositories.models import Repository


class RepositoryStatsViewSet(viewsets.ModelViewSet):
    """ViewSet for Repository Statistics"""

    serializer_class = RepositoryStatsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            RepositoryStats.objects.filter(user=self.request.user)
            .select_related("repository", "user")
            .order_by("-collected_at")
        )

    @action(detail=False, methods=["get"], url_path="latest")
    def latest_stats(self, request):
        latest_stats = []
        repositories = Repository.objects.filter(user=request.user)

        for repo in repositories:
            latest = (
                RepositoryStats.objects.filter(repository=repo, user=request.user)
                .order_by("-collected_at")
                .first()
            )
            if latest:
                latest_stats.append(latest)

        serializer = self.get_serializer(latest_stats, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="bulk-create")
    def bulk_create(self, request):
        serializer = BulkStatsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        created_stats = []

        for repo_data in data["repositories"]:
            repo_id = repo_data.get("repository_id")
            stats_data = repo_data.get("stats", {})

            try:
                repository = Repository.objects.get(id=repo_id, user=request.user)
                stat = RepositoryStats.objects.create(
                    repository=repository,
                    user=request.user,
                    stars=stats_data.get("stars", 0),
                    forks=stats_data.get("forks", 0),
                    watchers=stats_data.get("watchers", 0),
                    open_issues=stats_data.get("open_issues", 0),
                    subscribers=stats_data.get("subscribers", 0),
                    network=stats_data.get("network", 0),
                    size=stats_data.get("size", 0),
                    default_branch=stats_data.get("default_branch", ""),
                    description=stats_data.get("description", ""),
                    language=stats_data.get("language", ""),
                )
                created_stats.append(stat)
            except Repository.DoesNotExist:
                continue

        serializer = self.get_serializer(created_stats, many=True)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["get"], url_path="trend")
    def trend(self, request, pk=None):
        stats = self.get_queryset().filter(repository_id=pk).order_by("collected_at")
        if not stats.exists():
            return Response(
                {"detail": "No stats found for this repository"},
                status=status.HTTP_404_NOT_FOUND,
            )
        serializer = self.get_serializer(stats, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="summary")
    def summary(self, request):
        user = request.user
        latest_stats = {}
        for repo in Repository.objects.filter(user=user):
            latest = (
                RepositoryStats.objects.filter(repository=repo, user=user)
                .order_by("-collected_at")
                .first()
            )
            if latest:
                latest_stats[repo.id] = latest

        if not latest_stats:
            return Response(
                {
                    "total_repositories": 0,
                    "total_stars": 0,
                    "total_forks": 0,
                    "language_distribution": {},
                    "last_updated": None,
                }
            )

        total_stars = sum(stat.stars for stat in latest_stats.values())
        total_forks = sum(stat.forks for stat in latest_stats.values())
        most_starred = max(latest_stats.values(), key=lambda x: x.stars)
        most_forked = max(latest_stats.values(), key=lambda x: x.forks)

        language_dist = {}
        for stat in latest_stats.values():
            lang = stat.language or "Unknown"
            language_dist[lang] = language_dist.get(lang, 0) + 1

        last_updated = max(stat.collected_at for stat in latest_stats.values())

        data = {
            "total_repositories": len(latest_stats),
            "total_stars": total_stars,
            "total_forks": total_forks,
            "most_starred_repo": {
                "name": most_starred.repository.name,
                "stars": most_starred.stars,
                "full_name": most_starred.repository.full_name,
            },
            "most_forked_repo": {
                "name": most_forked.repository.name,
                "forks": most_forked.forks,
                "full_name": most_forked.repository.full_name,
            },
            "language_distribution": language_dist,
            "last_updated": last_updated,
        }

        summary_serializer = StatsSummarySerializer(data=data)
        summary_serializer.is_valid(raise_exception=True)
        return Response(summary_serializer.data)


class UserStatsViewSet(viewsets.ModelViewSet):
    serializer_class = UserStatsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserStats.objects.filter(user=self.request.user).order_by(
            "-collected_at"
        )

    @action(detail=False, methods=["get"], url_path="latest")
    def latest_stats(self, request):
        latest = self.get_queryset().first()
        if not latest:
            return Response(
                {
                    "total_repos": 0,
                    "total_stars": 0,
                    "total_forks": 0,
                    "total_watchers": 0,
                    "total_open_issues": 0,
                    "public_repos": 0,
                    "private_repos": 0,
                    "followers": 0,
                    "following": 0,
                    "contributions": 0,
                }
            )
        serializer = self.get_serializer(latest)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="update")
    def update_stats(self, request):
        stats_data = request.data
        stats = UserStats.objects.create(
            user=request.user,
            total_repos=stats_data.get("total_repos", 0),
            total_stars=stats_data.get("total_stars", 0),
            total_forks=stats_data.get("total_forks", 0),
            total_watchers=stats_data.get("total_watchers", 0),
            total_open_issues=stats_data.get("total_open_issues", 0),
            public_repos=stats_data.get("public_repos", 0),
            private_repos=stats_data.get("private_repos", 0),
            followers=stats_data.get("followers", 0),
            following=stats_data.get("following", 0),
            contributions=stats_data.get("contributions", 0),
        )
        serializer = self.get_serializer(stats)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class UpdateLogViewSet(viewsets.ModelViewSet):
    serializer_class = UpdateLogSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UpdateLog.objects.filter(user=self.request.user).order_by("-started_at")

    def perform_create(self, serializer):
        serializer.save(
            user=self.request.user, status="PENDING", repositories_updated=0
        )

    def create(self, request, *args, **kwargs):
        data = request.data.copy()
        if "status" not in data:
            data["status"] = "PENDING"
        if "repositories_updated" not in data:
            data["repositories_updated"] = 0

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(
            serializer.data, status=status.HTTP_201_CREATED, headers=headers
        )

    @action(detail=True, methods=["post"], url_path="complete")
    def complete_log(self, request, pk=None):
        log = self.get_object()
        log.status = "SUCCESS"
        log.completed_at = timezone.now()
        log.save()
        serializer = self.get_serializer(log)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="fail")
    def fail_log(self, request, pk=None):
        log = self.get_object()
        log.status = "FAILED"
        log.completed_at = timezone.now()
        log.error_message = request.data.get("error_message", "")
        log.save()
        serializer = self.get_serializer(log)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="recent")
    def recent_logs(self, request):
        seven_days_ago = timezone.now() - timedelta(days=7)
        logs = self.get_queryset().filter(started_at__gte=seven_days_ago)
        serializer = self.get_serializer(logs, many=True)
        return Response(serializer.data)


class ContributorViewSet(viewsets.ModelViewSet):
    """ViewSet for Contributors"""

    serializer_class = ContributorSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return (
            Contributor.objects.filter(user=self.request.user)
            .select_related("repository")
            .prefetch_related("languages")
        )

    @action(detail=False, methods=["post"], url_path="bulk-create")
    def bulk_create(self, request):
        """Bulk create contributors for a repository"""
        try:
            serializer = ContributorBulkCreateSerializer(data=request.data)
            if not serializer.is_valid():
                return Response(
                    {"error": "Invalid data", "details": serializer.errors},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            data = serializer.validated_data
            repository_id = data["repository_id"]
            contributors_data = data["contributors"]

            try:
                repository = Repository.objects.get(id=repository_id, user=request.user)
            except Repository.DoesNotExist:
                return Response(
                    {"error": "Repository not found"}, status=status.HTTP_404_NOT_FOUND
                )

            created_contributors = []
            errors = []

            for idx, contributor_data in enumerate(contributors_data):
                try:
                    github_id = contributor_data.get("id")
                    if not github_id:
                        errors.append({"index": idx, "error": "Missing github_id"})
                        continue

                    login = contributor_data.get("login", "")
                    if not login:
                        errors.append({"index": idx, "error": "Missing login"})
                        continue

                    # Get or create contributor
                    contributor, created = Contributor.objects.get_or_create(
                        repository=repository,
                        github_id=github_id,
                        defaults={
                            "user": request.user,
                            "login": login,
                            "avatar_url": contributor_data.get("avatar_url", ""),
                            "html_url": contributor_data.get("html_url", ""),
                            "contributions": contributor_data.get("contributions", 0),
                            "recent_commits": contributor_data.get(
                                "recent_commits", []
                            ),
                        },
                    )

                    # Update existing contributor
                    if not created:
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
                        contributor.recent_commits = contributor_data.get(
                            "recent_commits", contributor.recent_commits
                        )
                        contributor.save()

                    # Handle languages
                    languages_data = contributor_data.get("languages", [])

                    # Clear existing languages if updating
                    if not created:
                        contributor.languages.all().delete()

                    # Create language entries
                    for lang_data in languages_data:
                        language = lang_data.get("language", "")
                        if language:
                            try:
                                ContributorLanguages.objects.create(
                                    contributor=contributor,
                                    language=language,
                                    bytes=lang_data.get("bytes", 0),
                                    percentage=lang_data.get("percentage", 0.00),
                                )
                            except Exception as lang_error:
                                errors.append(
                                    {
                                        "index": idx,
                                        "login": login,
                                        "error": f"Language error: {str(lang_error)}",
                                    }
                                )

                    created_contributors.append(contributor)

                except Exception as e:
                    errors.append(
                        {
                            "index": idx,
                            "login": contributor_data.get("login", "unknown"),
                            "error": str(e),
                        }
                    )
                    continue

            if errors:
                return Response(
                    {
                        "success": True,
                        "created": len(created_contributors),
                        "errors": errors,
                        "message": f"Created {len(created_contributors)} contributors with {len(errors)} errors",
                    },
                    status=status.HTTP_207_MULTI_STATUS,
                )

            serializer = self.get_serializer(created_contributors, many=True)
            return Response(
                {
                    "success": True,
                    "created": len(created_contributors),
                    "data": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )

        except Exception as e:
            import traceback

            print("Error in bulk_create:", traceback.format_exc())
            return Response(
                {"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=["get"], url_path="languages")
    def get_languages(self, request, pk=None):
        """Get languages for a specific contributor"""
        contributor = self.get_object()
        languages = contributor.languages.all()
        serializer = ContributorLanguagesSerializer(languages, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="top-contributors")
    def top_contributors(self, request):
        """Get top contributors across all repositories"""
        limit = request.query_params.get("limit", 10)
        try:
            limit = int(limit)
        except ValueError:
            limit = 10

        contributors = self.get_queryset().order_by("-contributions")[:limit]
        serializer = self.get_serializer(contributors, many=True)
        return Response(serializer.data)


# ======================
# CONTRIBUTOR ACTIVITY VIEWSET
# ======================


class ContributorActivityViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing ContributorActivity.
    Provides CRUD operations and custom actions for analytics.
    """

    serializer_class = ContributorActivitySerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Optionally filters the queryset by repository_contributor_id,
        repository_id, or date range.
        """
        queryset = ContributorActivity.objects.filter(
            repository_contributor__user=self.request.user
        ).select_related(
            "repository_contributor__user", "repository_contributor__repository"
        )

        # Filter by repository contributor
        contributor_id = self.request.query_params.get("contributor_id")
        if contributor_id:
            queryset = queryset.filter(repository_contributor_id=contributor_id)

        # Filter by repository
        repository_id = self.request.query_params.get("repository_id")
        if repository_id:
            queryset = queryset.filter(
                repository_contributor__repository_id=repository_id
            )

        # Filter by date range
        start_date = self.request.query_params.get("start_date")
        end_date = self.request.query_params.get("end_date")
        if start_date:
            queryset = queryset.filter(period_start__gte=start_date)
        if end_date:
            queryset = queryset.filter(period_end__lte=end_date)

        # Filter by period type (daily, weekly, monthly)
        period_type = self.request.query_params.get("period_type")
        if period_type:
            if period_type == "daily":
                queryset = queryset.filter(period_end__date__gt=F("period_start__date"))
            elif period_type == "weekly":
                queryset = queryset.filter(
                    period_end__date__gt=F("period_start__date") + timedelta(days=6)
                )
            elif period_type == "monthly":
                queryset = queryset.filter(
                    period_end__date__gt=F("period_start__date") + timedelta(days=27)
                )

        return queryset

    @action(detail=False, methods=["get"])
    def summary(self, request):
        """
        Get summary statistics for all contributor activities.
        """
        queryset = self.get_queryset()

        # Aggregate statistics
        summary = queryset.aggregate(
            total_commits=Sum("commits"),
            total_pull_requests=Sum("pull_requests"),
            total_reviews=Sum("reviews"),
            total_issues=Sum("issues"),
            total_additions=Sum("additions"),
            total_deletions=Sum("deletions"),
            avg_commits=Avg("commits"),
            avg_pull_requests=Avg("pull_requests"),
            avg_reviews=Avg("reviews"),
            avg_issues=Avg("issues"),
            total_contributors=Count("repository_contributor", distinct=True),
            total_activities=Count("id"),
        )

        return Response(summary)

    @action(detail=False, methods=["get"])
    def top_contributors(self, request):
        """
        Get top contributors based on activity scores.
        """
        queryset = self.get_queryset()

        # Limit the number of results
        limit = int(request.query_params.get("limit", 10))

        # Group by contributor and aggregate.
        # NOTE: activity_score is a Python @property on the model, not a DB
        # column, so it can't be referenced inside annotate()/order_by().
        # It's recomputed here from real fields via ExpressionWrapper.
        # Login/repo name are pulled via .values() instead of Avg() since
        # they're plain text fields, uniform per group.
        top_contributors = (
            queryset.values(
                "repository_contributor_id",
                "repository_contributor__login",
                "repository_contributor__repository__name",
            )
            .annotate(
                total_commits=Sum("commits"),
                total_pull_requests=Sum("pull_requests"),
                total_reviews=Sum("reviews"),
                total_issues=Sum("issues"),
                total_additions=Sum("additions"),
                total_deletions=Sum("deletions"),
                period_count=Count("id"),
                avg_activity_score=Avg(
                    ExpressionWrapper(
                        F("commits") * 1.0
                        + F("pull_requests") * 2.0
                        + F("reviews") * 1.5
                        + F("issues") * 1.0
                        + (F("additions") + F("deletions")) * 0.01,
                        output_field=FloatField(),
                    )
                ),
            )
            .order_by("-avg_activity_score")[:limit]
        )

        # Convert to list of dicts with proper field names
        result = []
        for item in top_contributors:
            result.append(
                {
                    "repository_contributor_id": item["repository_contributor_id"],
                    "contributor_login": item["repository_contributor__login"],
                    "repository_name": item["repository_contributor__repository__name"],
                    "total_commits": item["total_commits"],
                    "total_pull_requests": item["total_pull_requests"],
                    "total_reviews": item["total_reviews"],
                    "total_issues": item["total_issues"],
                    "total_additions": item["total_additions"],
                    "total_deletions": item["total_deletions"],
                    "avg_activity_score": (
                        round(item["avg_activity_score"], 2)
                        if item["avg_activity_score"] is not None
                        else 0
                    ),
                    "period_count": item["period_count"],
                }
            )

        return Response(result)

    @action(detail=True, methods=["get"])
    def trends(self, request, pk=None):
        """
        Get activity trends for a specific contributor.
        """
        activity = self.get_object()

        # Get the last 12 periods for this contributor
        trends = ContributorActivity.objects.filter(
            repository_contributor=activity.repository_contributor,
            repository_contributor__user=request.user,
        ).order_by("-period_start")[:12]

        serializer = self.get_serializer(trends, many=True)
        return Response(
            {
                "contributor": activity.repository_contributor.login,
                "repository": activity.repository_contributor.repository.name,
                "current_period": self.get_serializer(activity).data,
                "historical_trends": serializer.data,
                "trend_direction": self._calculate_trend(trends),
            }
        )

    def _calculate_trend(self, activities):
        """
        Calculate the trend direction based on activity scores.
        """
        if len(activities) < 2:
            return "insufficient_data"

        # Convert to list and sort by period_start
        sorted_activities = list(activities.order_by("period_start"))
        scores = [a.activity_score for a in sorted_activities]

        if len(scores) >= 3:
            # Check if the last 3 periods show an upward or downward trend
            recent_avg = sum(scores[-3:]) / 3
            older_avg = (
                sum(scores[:-3]) / 3 if len(scores) > 3 else sum(scores[:-1]) / 2
            )

            if recent_avg > older_avg * 1.1:
                return "increasing"
            elif recent_avg < older_avg * 0.9:
                return "decreasing"
            else:
                return "stable"
        return "stable"

    @action(detail=False, methods=["post"])
    def bulk_create(self, request):
        """
        Bulk create contributor activity records.
        """
        serializer = ContributorActivityBulkCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        created_activities = []
        errors = []

        for idx, activity_data in enumerate(data["activities"]):
            try:
                # Get the contributor
                contributor_id = activity_data.get("repository_contributor_id")
                if not contributor_id:
                    errors.append(
                        {"index": idx, "error": "Missing repository_contributor_id"}
                    )
                    continue

                try:
                    contributor = Contributor.objects.get(
                        id=contributor_id, user=request.user
                    )
                except Contributor.DoesNotExist:
                    errors.append(
                        {
                            "index": idx,
                            "error": f"Contributor with id {contributor_id} not found",
                        }
                    )
                    continue

                # Create activity
                activity = ContributorActivity.objects.create(
                    repository_contributor=contributor,
                    period_start=activity_data.get("period_start"),
                    period_end=activity_data.get("period_end"),
                    commits=activity_data.get("commits", 0),
                    pull_requests=activity_data.get("pull_requests", 0),
                    reviews=activity_data.get("reviews", 0),
                    issues=activity_data.get("issues", 0),
                    additions=activity_data.get("additions", 0),
                    deletions=activity_data.get("deletions", 0),
                )
                created_activities.append(activity)

            except Exception as e:
                errors.append({"index": idx, "error": str(e)})

        response_data = {
            "success": True,
            "created": len(created_activities),
            "errors": errors,
        }

        if created_activities:
            response_data["data"] = self.get_serializer(
                created_activities, many=True
            ).data

        status_code = (
            status.HTTP_201_CREATED
            if created_activities
            else status.HTTP_400_BAD_REQUEST
        )
        return Response(response_data, status=status_code)

    @action(detail=False, methods=["get"])
    def analytics(self, request):
        """
        Advanced analytics for contributor activities.
        """
        queryset = self.get_queryset()

        # Get date range
        days = int(request.query_params.get("days", 30))
        since = timezone.now() - timedelta(days=days)

        # Filter activities for the last N days
        recent_activities = queryset.filter(period_start__gte=since)

        # Calculate activity metrics
        total = recent_activities.aggregate(
            total_commits=Sum("commits"),
            total_prs=Sum("pull_requests"),
            total_reviews=Sum("reviews"),
            total_issues=Sum("issues"),
            total_additions=Sum("additions"),
            total_deletions=Sum("deletions"),
            active_contributors=Count("repository_contributor", distinct=True),
        )

        # Sum()/Count() return None (not 0) when there are no matching rows,
        # e.g. no ContributorActivity records in the last N days. Coalesce
        # everything to 0 up front so downstream math/serialization is safe.
        total["total_commits"] = total.get("total_commits") or 0
        total["total_prs"] = total.get("total_prs") or 0
        total["total_reviews"] = total.get("total_reviews") or 0
        total["total_issues"] = total.get("total_issues") or 0
        total["total_additions"] = total.get("total_additions") or 0
        total["total_deletions"] = total.get("total_deletions") or 0
        total["active_contributors"] = total.get("active_contributors") or 0

        # Calculate activity velocity (average per day)
        if days > 0:
            total["velocity"] = {
                "commits_per_day": round(total["total_commits"] / days, 2),
                "prs_per_day": round(total["total_prs"] / days, 2),
                "reviews_per_day": round(total["total_reviews"] / days, 2),
                "issues_per_day": round(total["total_issues"] / days, 2),
            }

        # Get top performers
        top_performers = (
            recent_activities.values("repository_contributor__login")
            .annotate(
                total_commits=Sum("commits"),
                total_prs=Sum("pull_requests"),
                total_reviews=Sum("reviews"),
                total_issues=Sum("issues"),
            )
            .order_by("-total_commits")[:5]
        )

        return Response(
            {
                "period": {"days": days, "since": since, "until": timezone.now()},
                "summary": total,
                "top_performers": top_performers,
                "recent_activities": self.get_serializer(
                    recent_activities.order_by("-period_start")[:10], many=True
                ).data,
            }
        )
