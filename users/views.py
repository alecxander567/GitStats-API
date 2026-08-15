import json
import firebase_admin
from firebase_admin import auth, credentials
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authtoken.models import Token
from django.contrib.auth import logout
from django.db.models import Q  # Add this import
from .models import User
from .serializers import UserSerializer  # Add this import
import os
import requests
from rest_framework import generics, permissions

# Firebase credentials are loaded from an env var containing the full
# service account JSON (not a file path) - this works on hosts like
# Render where you can't commit the credentials file to the repo.
firebase_creds_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")

if not firebase_admin._apps:
    try:
        if firebase_creds_json:
            cred_dict = json.loads(firebase_creds_json)
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            print("Firebase initialized from FIREBASE_CREDENTIALS_JSON env var")
        else:
            print("FIREBASE_CREDENTIALS_JSON env var not set")
    except Exception as e:
        print(f"Error initializing Firebase: {e}")


class FirebaseAuthView(APIView):
    def post(self, request):
        id_token = request.data.get("idToken")
        github_token = request.data.get("github_token")

        if not id_token:
            return Response(
                {"message": "ID token is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            if not firebase_admin._apps:
                return Response(
                    {"message": "Firebase not initialized. Check credentials file."},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                )

            decoded_token = auth.verify_id_token(id_token)
            uid = decoded_token.get("user_id")
            firebase_user = auth.get_user(uid)

            github_provider = None
            for provider in firebase_user.provider_data:
                if provider.provider_id == "github.com":
                    github_provider = provider
                    break

            if not github_provider:
                return Response(
                    {"message": "Only GitHub authentication is allowed"},
                    status=status.HTTP_403_FORBIDDEN,
                )

            github_id = github_provider.uid

            # Fetch GitHub user data if token is available
            github_user_data = {}
            if github_token:
                try:
                    headers = {"Authorization": f"token {github_token}"}
                    github_response = requests.get(
                        "https://api.github.com/user", headers=headers, timeout=10
                    )
                    if github_response.status_code == 200:
                        github_user_data = github_response.json()
                except Exception as e:
                    print(f"Error fetching GitHub data: {e}")

            # The real GitHub handle is the "login" field from /user -
            # NOT "name" (that's the person's display name and can have
            # spaces/punctuation). This is what's valid in profile URLs
            # and badge/stat services.
            real_github_username = github_user_data.get("login") or None

            user, created = User.objects.get_or_create(
                github_id=github_id,
                defaults={
                    # Use the real login for `username` too when we have
                    # it, so new users don't get stuck with a
                    # "github_<id>" placeholder from day one.
                    "username": real_github_username or f"github_{github_id}",
                    "github_username": real_github_username,
                    "display_name": firebase_user.display_name
                    or github_user_data.get("name")
                    or real_github_username
                    or "User",
                    "email": firebase_user.email or github_user_data.get("email") or "",
                    "avatar_url": firebase_user.photo_url
                    or github_user_data.get("avatar_url")
                    or "",
                    "access_token": id_token,
                    "github_token": github_token,
                    "followers": github_user_data.get("followers", 0),
                    "following": github_user_data.get("following", 0),
                    "public_repos": github_user_data.get("public_repos", 0),
                    "bio": github_user_data.get("bio", ""),
                    "location": github_user_data.get("location", ""),
                    "company": github_user_data.get("company", ""),
                    "blog": github_user_data.get("blog", ""),
                },
            )

            if not created:
                if github_token:
                    user.github_token = github_token
                if github_user_data:
                    user.followers = github_user_data.get(
                        "followers", user.followers or 0
                    )
                    user.following = github_user_data.get(
                        "following", user.following or 0
                    )
                    user.public_repos = github_user_data.get(
                        "public_repos", user.public_repos or 0
                    )
                    user.bio = github_user_data.get("bio", user.bio or "")
                    user.location = github_user_data.get(
                        "location", user.location or ""
                    )
                    user.company = github_user_data.get("company", user.company or "")
                    user.blog = github_user_data.get("blog", user.blog or "")
                    user.display_name = (
                        github_user_data.get("name") or user.display_name
                    )
                    user.avatar_url = (
                        github_user_data.get("avatar_url") or user.avatar_url
                    )
                # Backfill/refresh the real GitHub username whenever we
                # manage to get one. This heals every existing user
                # (including "github_162329514"-style accounts) the
                # next time they log in.
                if real_github_username:
                    user.github_username = real_github_username
                user.display_name = firebase_user.display_name or user.display_name
                user.email = firebase_user.email or user.email
                user.avatar_url = firebase_user.photo_url or user.avatar_url
                user.access_token = id_token
                user.save()

            token, _ = Token.objects.get_or_create(user=user)

            user_data = {
                "id": user.id,
                "username": user.username,
                "github_username": user.github_username,
                "email": user.email,
                "display_name": user.display_name,
                "avatar_url": user.avatar_url,
                "github_token": user.github_token,
                "followers": user.followers,
                "following": user.following,
                "public_repos": user.public_repos,
                "bio": user.bio,
                "location": user.location,
                "company": user.company,
                "blog": user.blog,
            }

            return Response(
                {
                    "message": "Authentication successful",
                    "user": user_data,
                    "token": token.key,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            print(f"Error: {e}")
            return Response(
                {"message": f"Authentication failed: {str(e)}"},
                status=status.HTTP_401_UNAUTHORIZED,
            )


class UserMeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user_data = {
            "id": request.user.id,
            "username": request.user.username,
            "github_username": request.user.github_username,
            "email": request.user.email,
            "display_name": request.user.display_name,
            "avatar_url": request.user.avatar_url,
            "github_token": request.user.github_token,
            "followers": request.user.followers,
            "following": request.user.following,
            "public_repos": request.user.public_repos,
            "bio": request.user.bio,
            "location": request.user.location,
            "company": request.user.company,
            "blog": request.user.blog,
        }
        return Response(user_data)


class UserLogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            request.user.auth_token.delete()
            logout(request)
            return Response(
                {"message": "Logged out successfully"}, status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response(
                {"message": f"Logout failed: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class AddGitHubTokenView(APIView):
    """Called by the frontend's `syncGithub()` - re-validates the stored
    GitHub token and refreshes profile stats."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        github_token = request.data.get("github_token")

        if not github_token:
            return Response(
                {"message": "GitHub token is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            headers = {"Authorization": f"token {github_token}"}
            test_response = requests.get(
                "https://api.github.com/user", headers=headers, timeout=10
            )

            if test_response.status_code != 200:
                return Response(
                    {"message": "Invalid GitHub token"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            github_data = test_response.json()

            user = request.user
            user.github_token = github_token
            # This is the other place a user can end up connecting their
            # account (via "Sync repos" in the frontend) - capture/heal
            # github_username here too, not just at initial login.
            if github_data.get("login"):
                user.github_username = github_data["login"]
            user.display_name = github_data.get("name") or user.display_name
            user.avatar_url = github_data.get("avatar_url") or user.avatar_url
            user.bio = github_data.get("bio", user.bio or "")
            user.location = github_data.get("location", user.location or "")
            user.company = github_data.get("company", user.company or "")
            user.blog = github_data.get("blog", user.blog or "")
            user.followers = github_data.get("followers", user.followers or 0)
            user.following = github_data.get("following", user.following or 0)
            user.public_repos = github_data.get("public_repos", user.public_repos or 0)
            user.save()

            return Response(
                {
                    "message": "GitHub token added successfully",
                    "github_username": user.github_username,
                    "github_token": user.github_token,
                    "followers": user.followers,
                    "following": user.following,
                    "public_repos": user.public_repos,
                },
                status=status.HTTP_200_OK,
            )

        except Exception as e:
            return Response(
                {"message": f"Failed to add GitHub token: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class RemoveGitHubTokenView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            user = request.user
            user.github_token = None
            user.save()
            return Response(
                {"message": "GitHub token removed successfully"},
                status=status.HTTP_200_OK,
            )
        except Exception as e:
            return Response(
                {"message": f"Failed to remove GitHub token: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class GitHubExchangeView(APIView):
    """Exchanges a GitHub OAuth `code` for an access token server-side,
    so the client secret never touches the browser."""

    def post(self, request):
        code = request.data.get("code")

        if not code:
            return Response(
                {"message": "code is required"}, status=status.HTTP_400_BAD_REQUEST
            )

        try:
            resp = requests.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.GITHUB_CLIENT_ID,
                    "client_secret": settings.GITHUB_CLIENT_SECRET,
                    "code": code,
                },
                timeout=10,
            )
            data = resp.json()

            if "access_token" not in data:
                return Response(
                    {"message": "GitHub token exchange failed", "detail": data},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                {"github_token": data["access_token"]}, status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"message": f"GitHub exchange failed: {str(e)}"},
                status=status.HTTP_400_BAD_REQUEST,
            )


class UserListView(generics.ListAPIView):
    """
    List all users - for search functionality
    """

    permission_classes = [IsAuthenticated]
    serializer_class = UserSerializer

    def get_queryset(self):
        queryset = User.objects.all().only(
            "id", "username", "email", "display_name", "avatar_url"
        )

        # Add search filtering
        search = self.request.query_params.get("q", "")
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(display_name__icontains=search)
            )

        return queryset[:50]  # Limit results
