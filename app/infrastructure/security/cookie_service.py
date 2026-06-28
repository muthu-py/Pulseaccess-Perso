from fastapi import Response

from app.core.config import Settings


class CookieService:
    """Manages the HttpOnly refresh token cookie on HTTP responses."""

    def __init__(self, settings: Settings) -> None:
        self._cookie_name = settings.COOKIE_NAME
        self._domain = settings.COOKIE_DOMAIN
        self._path = settings.COOKIE_PATH
        self._secure = settings.COOKIE_SECURE
        self._httponly = settings.COOKIE_HTTPONLY
        self._samesite = settings.COOKIE_SAMESITE

    def set_refresh_cookie(self, response: Response, token: str, max_age_days: int = 30) -> None:
        """Set the refresh token as an HttpOnly cookie on the response."""
        response.set_cookie(
            key=self._cookie_name,
            value=token,
            max_age=max_age_days * 24 * 60 * 60,
            domain=self._domain,
            path=self._path,
            secure=self._secure,
            httponly=self._httponly,
            samesite=self._samesite,
        )

    def clear_refresh_cookie(self, response: Response) -> None:
        """Delete the refresh token cookie from the response."""
        response.delete_cookie(
            key=self._cookie_name,
            domain=self._domain,
            path=self._path,
            secure=self._secure,
            httponly=self._httponly,
            samesite=self._samesite,
        )
