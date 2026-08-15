from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from django.db.models import Count, Avg, Min, Max
from django.shortcuts import get_object_or_404
from .models import ProjectCategory
from .serializers import (
    ProjectCategorySerializer,
    ProjectCategoryCreateSerializer,
    ProjectCategoryBulkCreateSerializer,
    ProjectCategoryStatsSerializer,
)
from repositories.models import Repository


class ProjectCategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ProjectCategory operations.
    Supports list, create, retrieve, update, delete, and custom actions.
    """

    queryset = ProjectCategory.objects.select_related(
        "repository", "repository__user"
    ).all()
    serializer_class = ProjectCategorySerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return ProjectCategoryCreateSerializer
        return ProjectCategorySerializer

    def get_queryset(self):
        queryset = super().get_queryset()

        # Filter by repository_id if provided
        repository_id = self.request.query_params.get("repository_id")
        if repository_id:
            queryset = queryset.filter(repository_id=repository_id)

        # Filter by category if provided
        category = self.request.query_params.get("category")
        if category:
            queryset = queryset.filter(category=category)

        # Filter by minimum confidence
        min_confidence = self.request.query_params.get("min_confidence")
        if min_confidence:
            queryset = queryset.filter(confidence__gte=min_confidence)

        return queryset

    def create(self, request, *args, **kwargs):
        """
        Create a single project category.
        """
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        repository_id = serializer.validated_data["repository_id"]
        category = serializer.validated_data["category"]
        confidence = serializer.validated_data["confidence"]

        # Check if repository exists
        repository = get_object_or_404(Repository, id=repository_id)

        # Create or update
        obj, created = ProjectCategory.objects.update_or_create(
            repository=repository,
            category=category,
            defaults={"confidence": confidence},
        )

        output_serializer = ProjectCategorySerializer(obj)
        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=False, methods=["post"], permission_classes=[IsAuthenticated])
    def bulk_create(self, request):
        """
        Bulk create/update project categories.
        Expects: {"categories": [{"repository_id": 1, "category": "Web", "confidence": 95.50}, ...]}
        """
        serializer = ProjectCategoryBulkCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        categories_data = serializer.validated_data["categories"]
        created_objects = []
        updated_objects = []

        for category_data in categories_data:
            repository_id = category_data["repository_id"]
            category = category_data["category"]
            confidence = category_data["confidence"]

            repository = get_object_or_404(Repository, id=repository_id)

            obj, created = ProjectCategory.objects.update_or_create(
                repository=repository,
                category=category,
                defaults={"confidence": confidence},
            )

            if created:
                created_objects.append(obj)
            else:
                updated_objects.append(obj)

        # Serialize all objects
        all_objects = created_objects + updated_objects
        output_serializer = ProjectCategorySerializer(all_objects, many=True)

        return Response(
            {
                "created": len(created_objects),
                "updated": len(updated_objects),
                "data": output_serializer.data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def stats(self, request):
        """
        Get statistics about project categories.
        """
        queryset = self.get_queryset()

        # Filter by repository if needed
        repository_id = request.query_params.get("repository_id")
        if repository_id:
            queryset = queryset.filter(repository_id=repository_id)

        stats = (
            queryset.values("category")
            .annotate(
                count=Count("id"),
                avg_confidence=Avg("confidence"),
                min_confidence=Min("confidence"),
                max_confidence=Max("confidence"),
            )
            .order_by("-count")
        )

        serializer = ProjectCategoryStatsSerializer(stats, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"], permission_classes=[IsAuthenticated])
    def recalculate_confidence(self, request, pk=None):
        """
        Recalculate confidence for a specific category (placeholder for ML integration).
        """
        obj = self.get_object()
        return Response(
            {
                "id": obj.id,
                "repository": obj.repository.name,
                "category": obj.category,
                "old_confidence": obj.confidence,
                "message": "Confidence recalculation placeholder - integrate ML model here",
            }
        )

    @action(detail=False, methods=["get"])
    def by_repository(self, request):
        """
        Get all categories for a specific repository.
        """
        repository_id = request.query_params.get("repository_id")
        if not repository_id:
            return Response(
                {"error": "repository_id parameter is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        queryset = self.get_queryset().filter(repository_id=repository_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
