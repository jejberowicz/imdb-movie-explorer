"""Configuration from environment variables. The defaults only make sense for local development."""

import os
from dataclasses import dataclass

DEFAULT_DATABASE_URL = "postgresql+psycopg://movies:movies@localhost:5432/movies"


@dataclass(frozen=True)
class Settings:
    database_url: str = DEFAULT_DATABASE_URL
    # Requests per client IP, in the syntax of Flask-Limiter. Searching as you type, with the 300 ms debounce
    # of the front, stays far below it.
    rate_limit: str = "300 per minute"
    # Proxies in front of the API that add X-Forwarded-For (nginx in Docker: 1). With 0, the client IP is the
    # one of the connection; trusting the header without a proxy would let anyone fake their IP.
    proxy_hops: int = 0

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            database_url=os.environ.get("DATABASE_URL", DEFAULT_DATABASE_URL),
            rate_limit=os.environ.get("RATE_LIMIT", cls.rate_limit),
            proxy_hops=int(os.environ.get("PROXY_HOPS", cls.proxy_hops)),
        )
