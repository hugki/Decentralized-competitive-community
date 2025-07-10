import os
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    jwt_secret: str = Field(..., env="JWT_SECRET")
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24

    github_jwks_url: str = (
        "https://token.actions.githubusercontent.com/.well-known/jwks"
    )

    class Config:
        env_file = ".env"

@lru_cache
def get_settings() -> Settings:
    return Settings()
