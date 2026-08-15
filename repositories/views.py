from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Count, Sum, Q
from django.shortcuts import get_object_or_404
from .models import Repository
from .serializers import (
    RepositorySerializer,
    RepositoryCreateUpdateSerializer,
    RepositoryListSerializer,
    RepositoryStatsSerializer,
)
from analytics.models import Contributor  # NEW — needed for RepositoryUserCommitsView
import requests


class IsOwnerOrReadOnly(permissions.BasePermission):
    """Custom permission to only allow owners to edit their repositories"""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.user == request.user


class RepositoryListView(generics.ListCreateAPIView):
    """
    List all repositories for the authenticated user or create a new repository.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == "POST":
            return RepositoryCreateUpdateSerializer
        return RepositoryListSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = Repository.objects.filter(user=user)

        # Filter by visibility
        visibility = self.request.query_params.get("visibility")
        if visibility:
            queryset = queryset.filter(visibility=visibility)

        # Filter by archived
        archived = self.request.query_params.get("archived")
        if archived is not None:
            archived_bool = archived.lower() == "true"
            queryset = queryset.filter(archived=archived_bool)

        # Filter by language
        language = self.request.query_params.get("language")
        if language:
            queryset = queryset.filter(primary_language=language)

        # Search by name
        search = self.request.query_params.get("search")
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) | Q(full_name__icontains=search)
            )

        # Ordering
        ordering = self.request.query_params.get("ordering", "-updated_at_github")
        allowed_orderings = [
            "name",
            "-name",
            "stars",
            "-stars",
            "forks",
            "-forks",
            "created_at_github",
            "-created_at_github",
            "updated_at_github",
            "-updated_at_github",
        ]
        if ordering in allowed_orderings:
            queryset = queryset.order_by(ordering)

        return queryset

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class RepositoryDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update or delete a repository instance.
    """

    permission_classes = [permissions.IsAuthenticated, IsOwnerOrReadOnly]
    queryset = Repository.objects.all()

    def get_serializer_class(self):
        if self.request.method in ["PUT", "PATCH"]:
            return RepositoryCreateUpdateSerializer
        return RepositorySerializer

    def get_queryset(self):
        return Repository.objects.filter(user=self.request.user)


class RepositoryStatsView(APIView):
    """
    Get statistics for the authenticated user's repositories.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        repos = Repository.objects.filter(user=user)

        # Calculate languages
        languages = (
            repos.values("primary_language")
            .annotate(count=Count("id"))
            .order_by("-count")
        )
        languages_dict = {
            item["primary_language"]: item["count"]
            for item in languages
            if item["primary_language"]
        }

        stats = {
            "total_repos": repos.count(),
            "public_repos": repos.filter(visibility="public").count(),
            "private_repos": repos.filter(visibility="private").count(),
            "archived_repos": repos.filter(archived=True).count(),
            "total_stars": repos.aggregate(Sum("stars"))["stars__sum"] or 0,
            "total_forks": repos.aggregate(Sum("forks"))["forks__sum"] or 0,
            "languages": languages_dict,
        }

        serializer = RepositoryStatsSerializer(stats)
        return Response(serializer.data)


class BulkCreateRepositoriesView(APIView):
    """
    Bulk create or update repositories from GitHub API data.
    """

    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        repositories_data = request.data.get("repositories", [])

        if not repositories_data:
            return Response(
                {"error": "No repositories data provided"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_count = 0
        updated_count = 0
        errors = []

        for repo_data in repositories_data:
            try:
                github_id = repo_data.get("github_repo_id")
                if not github_id:
                    errors.append(
                        {"error": "github_repo_id is required", "data": repo_data}
                    )
                    continue

                # Check if repository exists
                repo, created = Repository.objects.update_or_create(
                    user=request.user, github_repo_id=github_id, defaults=repo_data
                )

                if created:
                    created_count += 1
                else:
                    updated_count += 1

            except Exception as e:
                errors.append({"error": str(e), "data": repo_data})

        return Response(
            {
                "message": "Bulk repository sync completed",
                "created": created_count,
                "updated": updated_count,
                "errors": errors,
            },
            status=status.HTTP_201_CREATED,
        )


class RepositoryLanguagesView(APIView):
    """
    Get unique languages used by the user's repositories.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        languages = (
            Repository.objects.filter(user=request.user, primary_language__isnull=False)
            .values_list("primary_language", flat=True)
            .distinct()
            .order_by("primary_language")
        )
        return Response(list(languages))


class RepositoryUserCommitsView(APIView):
    """
    Returns the signed-in user's recent commits for a repository, as
    captured during the last sync (see analytics.Contributor.recent_commits
    and hooks/useGithubSync.js on the frontend).

    IMPORTANT: this deliberately does NOT hit the GitHub API live. It reads
    whatever the sync pipeline already stored, so it stays fast, doesn't
    burn GitHub rate limit on every dashboard load, and stays consistent
    with what the sync actually captured (paginated, retried on 403/429).

    Matches the Contributor row by github_id rather than username/login —
    Django's `username` has no guaranteed relationship to the GitHub
    login, but github_id is stable and captured on both User and
    Contributor at sync/OAuth time.
    """

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        repository = get_object_or_404(Repository, pk=pk, user=request.user)

        if not request.user.github_id:
            return Response(
                {
                    "error": "GitHub account not connected.",
                    "commits": [],
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        contributor = Contributor.objects.filter(
            repository=repository,
            user=request.user,
            github_id=request.user.github_id,
        ).first()

        if not contributor:
            # Not an error — the repo may not have been synced yet, or the
            # signed-in user isn't a contributor on it.
            return Response(
                {
                    "repository_id": repository.id,
                    "repository_name": repository.name,
                    "commits": [],
                }
            )

        return Response(
            {
                "repository_id": repository.id,
                "repository_name": repository.name,
                "commits": contributor.recent_commits or [],
            }
        )
