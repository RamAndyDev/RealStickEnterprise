from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = 'development'
    api_prefix: str = '/api/v1'
    cors_origins: str = 'http://localhost:5173'
    supabase_url: str
    supabase_service_role_key: str
    # Unused for access-token verification (project uses ES256 JWKS). Kept optional for compatibility.
    supabase_jwt_secret: str | None = None
    # Used for Auth invite/recovery redirect (e.g. http://localhost:5173).
    frontend_app_url: str | None = None
    # Public website contact form (Resend). Server-side only — never expose to React.
    resend_api_key: str | None = None
    contact_to_email: str | None = None
    contact_from_email: str | None = None

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(',') if origin.strip()]

    @property
    def password_reset_redirect_url(self) -> str:
        base = (self.frontend_app_url or (self.cors_origin_list[0] if self.cors_origin_list else '')).rstrip(
            '/'
        )
        return f'{base}/reset-password' if base else '/reset-password'

    @property
    def supabase_jwt_issuer(self) -> str:
        return f"{self.supabase_url.rstrip('/')}/auth/v1"

    @property
    def supabase_jwks_url(self) -> str:
        return f"{self.supabase_jwt_issuer}/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()
