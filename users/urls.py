from django.urls import path
from .views import (
    FirebaseAuthView,
    UserMeView,
    UserLogoutView,
    AddGitHubTokenView,
    RemoveGitHubTokenView,
    GitHubExchangeView,
    UserListView,
)

app_name = "users"

urlpatterns = [
    # Auth endpoints
    path("users/auth/firebase/", FirebaseAuthView.as_view(), name="firebase_auth"),
    path("users/auth/me/", UserMeView.as_view(), name="user_me"),
    path("users/auth/logout/", UserLogoutView.as_view(), name="user_logout"),
    path("users/auth/github/add-token/", AddGitHubTokenView.as_view(), name="add_github_token"),
    path("users/auth/github/remove-token/", RemoveGitHubTokenView.as_view(), name="remove_github_token"),
    path("users/auth/github/exchange/", GitHubExchangeView.as_view(), name="github_exchange"),

    # User list / search endpoint
    path("users/list/", UserListView.as_view(), name="user_list"),
]