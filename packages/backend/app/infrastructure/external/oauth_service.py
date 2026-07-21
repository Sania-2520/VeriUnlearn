import secrets
from typing import Any, Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class OAuthProvider:
    GOOGLE = "google"
    GITHUB = "github"


class OAuthService:
    @staticmethod
    def get_authorization_url(provider: str) -> str:
        if provider == OAuthProvider.GOOGLE:
            return (
                f"https://accounts.google.com/o/oauth2/v2/auth?"
                f"client_id={settings.google_client_id}&"
                f"redirect_uri={settings.google_redirect_uri}&"
                f"response_type=code&"
                f"scope=openid%20email%20profile&"
                f"access_type=offline&"
                f"state={secrets.token_urlsafe(32)}"
            )
        elif provider == OAuthProvider.GITHUB:
            return (
                f"https://github.com/login/oauth/authorize?"
                f"client_id={settings.github_client_id}&"
                f"redirect_uri={settings.github_redirect_uri}&"
                f"scope=read:user%20user:email&"
                f"state={secrets.token_urlsafe(32)}"
            )
        raise ValueError(f"Unsupported OAuth provider: {provider}")

    @staticmethod
    async def exchange_code(
        provider: str, code: str
    ) -> dict[str, Any]:
        if provider == OAuthProvider.GOOGLE:
            return await OAuthService._exchange_google(code)
        elif provider == OAuthProvider.GITHUB:
            return await OAuthService._exchange_github(code)
        raise ValueError(f"Unsupported OAuth provider: {provider}")

    @staticmethod
    async def get_user_info(
        provider: str, access_token: str
    ) -> dict[str, Any]:
        if provider == OAuthProvider.GOOGLE:
            return await OAuthService._get_google_user(access_token)
        elif provider == OAuthProvider.GITHUB:
            return await OAuthService._get_github_user(access_token)
        raise ValueError(f"Unsupported OAuth provider: {provider}")

    @staticmethod
    async def _exchange_google(code: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "code": code,
                    "redirect_uri": settings.google_redirect_uri,
                    "grant_type": "authorization_code",
                },
            )
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    async def _exchange_github(code: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                "https://github.com/login/oauth/access_token",
                headers={"Accept": "application/json"},
                data={
                    "client_id": settings.github_client_id,
                    "client_secret": settings.github_client_secret,
                    "code": code,
                    "redirect_uri": settings.github_redirect_uri,
                },
            )
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    async def _get_google_user(access_token: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://www.googleapis.com/oauth2/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "provider": "google",
                "provider_user_id": data["id"],
                "email": data.get("email", ""),
                "full_name": data.get("name", ""),
                "avatar_url": data.get("picture", ""),
                "access_token": access_token,
            }

    @staticmethod
    async def _get_github_user(access_token: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                "https://api.github.com/user",
                headers={
                    "Authorization": f"token {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

            email_resp = await client.get(
                "https://api.github.com/user/emails",
                headers={
                    "Authorization": f"token {access_token}",
                    "Accept": "application/vnd.github.v3+json",
                },
            )
            email_resp.raise_for_status()
            emails = email_resp.json()
            primary_email = next(
                (e["email"] for e in emails if e.get("primary")),
                emails[0]["email"] if emails else "",
            )

            return {
                "provider": "github",
                "provider_user_id": str(data["id"]),
                "email": primary_email,
                "full_name": data.get("name") or data.get("login", ""),
                "avatar_url": data.get("avatar_url", ""),
                "access_token": access_token,
            }


oauth_service = OAuthService()
