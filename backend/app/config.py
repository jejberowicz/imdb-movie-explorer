"""Configuration from environment variables. The defaults only make sense for local development."""

import os
from dataclasses import dataclass

DEFAULT_DATABASE_URL = "postgresql+psycopg://movies:movies@localhost:5432/movies"


@dataclass(frozen=True)
class Settings:
    database_url: str = DEFAULT_DATABASE_URL

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(database_url=os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL))
