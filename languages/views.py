from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.db.models import Sum, Count, Avg, Q
from django.shortcuts import get_object_or_404
from .models import RepositoryLanguage
from .serializers import (
    RepositoryLanguageSerializer,
    RepositoryLanguageSummarySerializer,
    RepositoryLanguageCreateUpdateSerializer,
)
from repositories.models import Repository


class RepositoryLanguageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for RepositoryLanguage model with additional actions
    """

    queryset = RepositoryLanguage.objects.all()
    serializer_class = RepositoryLanguageSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        """
        Filter queryset based on query parameters
        """
        queryset = super().get_queryset()

        # Filter by repository_id
        repository_id = self.request.query_params.get("repository_id")
        if repository_id:
            queryset = queryset.filter(repository_id=repository_id)

        # Filter by language
        language = self.request.query_params.get("language")
        if language:
            queryset = queryset.filter(language__icontains=language)

        # Filter by minimum percentage
        min_percentage = self.request.query_params.get("min_percentage")
        if min_percentage:
            queryset = queryset.filter(percentage__gte=float(min_percentage))

        # Order by percentage (default) or bytes
        ordering = self.request.query_params.get("ordering", "-percentage")
        if ordering in ["percentage", "-percentage", "bytes", "-bytes"]:
            queryset = queryset.order_by(ordering)

        return queryset

    def create(self, request, *args, **kwargs):
        """
        Override create to handle both single and bulk creation
        """
        if isinstance(request.data, list):
            # Bulk creation
            serializer = self.get_serializer(data=request.data, many=True)
            if serializer.is_valid():
                self.perform_create(serializer)
                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        else:
            # Single creation
            return super().create(request, *args, **kwargs)

    @action(detail=False, methods=["post"], url_path="bulk-update")
    def bulk_update(self, request):
        """
        Bulk update or create languages for a repository
        Expected format:
        {
            "repository_id": 1,
            "languages": [
                {"language": "Python", "bytes": 1000, "percentage": 50.0},
                {"language": "JavaScript", "bytes": 1000, "percentage": 50.0}
            ]
        }
        """
        repository_id = request.data.get("repository_id")
        languages_data = request.data.get("languages", [])

        if not repository_id:
            return Response(
                {"error": "repository_id is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        repository = get_object_or_404(Repository, id=repository_id)

        # Validate and process languages
        serializer = RepositoryLanguageCreateUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Process each language
        created_languages = []
        for lang_data in languages_data:
            language_obj, created = RepositoryLanguage.objects.update_or_create(
                repository=repository,
                language=lang_data["language"],
                defaults={
                    "bytes": lang_data["bytes"],
                    "percentage": lang_data["percentage"],
                },
            )
            created_languages.append(language_obj)

        # Serialize and return the results
        serializer = RepositoryLanguageSerializer(created_languages, many=True)
        return Response(
            {
                "message": f"Updated {len(created_languages)} languages for {repository.name}",
                "data": serializer.data,
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=["get"])
    def get_languages_by_repository(self, request, pk=None):
        """
        Get all languages for a specific repository
        """
        repository = get_object_or_404(Repository, id=pk)
        languages = RepositoryLanguage.objects.filter(repository=repository)
        serializer = self.get_serializer(languages, many=True)
        return Response(
            {
                "repository": repository.name,
                "total_languages": languages.count(),
                "languages": serializer.data,
            }
        )

    @action(detail=False, methods=["get"], url_path="summary")
    def language_summary(self, request):
        """
        Get summary statistics for all languages across repositories
        """
        # Aggregate language statistics
        summary = (
            RepositoryLanguage.objects.values("language")
            .annotate(
                total_bytes=Sum("bytes"),
                total_repositories=Count("repository", distinct=True),
                average_percentage=Avg("percentage"),
            )
            .order_by("-total_bytes")
        )

        serializer = RepositoryLanguageSummarySerializer(summary, many=True)
        return Response(
            {"total_languages_used": summary.count(), "summary": serializer.data}
        )

    @action(detail=False, methods=["get"], url_path="search")
    def search_languages(self, request):
        """
        Search for languages
        """
        search_term = request.query_params.get("q", "")
        if not search_term:
            return Response(
                {"error": "Search term (q) is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        languages = (
            RepositoryLanguage.objects.filter(Q(language__icontains=search_term))
            .values("language")
            .annotate(total_repositories=Count("repository"), total_bytes=Sum("bytes"))
            .order_by("-total_repositories")
        )

        return Response({"search_term": search_term, "results": languages})

    @action(detail=False, methods=["delete"], url_path="cleanup")
    def cleanup_languages(self, request):
        """
        Delete languages with percentage less than 1% or 0 bytes
        """
        deleted_count = RepositoryLanguage.objects.filter(
            Q(percentage__lt=1.0) | Q(bytes=0)
        ).delete()[0]

        return Response(
            {
                "message": f"Deleted {deleted_count} language entries with less than 1% or 0 bytes"
            }
        )

    @action(detail=False, methods=["get"], url_path="top")
    def top_languages(self, request):
        """
        Get most used languages globally
        """
        limit = int(request.query_params.get("limit", 10))

        top_languages = (
            RepositoryLanguage.objects.values("language")
            .annotate(total_bytes=Sum("bytes"), total_repositories=Count("repository"))
            .order_by("-total_bytes")[:limit]
        )

        return Response({"top_languages": top_languages})
