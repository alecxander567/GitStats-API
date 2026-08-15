from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ReadmeProfileViewSet

router = DefaultRouter()
router.register(r"profile", ReadmeProfileViewSet, basename="readme-profile")

urlpatterns = [
    # Explicit mapping so PUT/PATCH on the bare "profile/" URL reach
    # update() directly. The router alone only wires PUT/PATCH to the
    # detail route (profile/<pk>/), never the list route (profile/),
    # which is why PUT was returning 405 before this.
    #
    # Both "put" and "patch" point at update() because update() already
    # does serializer.save() with partial=True internally (see views.py) -
    # it doesn't care which HTTP verb triggered it. This also avoids
    # calling the default partial_update(), which *would* try
    # self.get_object() with a pk that doesn't exist on this URL and 500.
    path(
        "profile/",
        ReadmeProfileViewSet.as_view(
            {
                "get": "list",
                "put": "update",
                "patch": "update",
            }
        ),
    ),
    # Router still handles create fallback and all @action routes:
    # regenerate/, export/, preview/, toggle_auto_update/, history/, templates/
    path("", include(router.urls)),
]
