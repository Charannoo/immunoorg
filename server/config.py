"""Server configuration."""

from pydantic import BaseModel


class ServerConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 7860
    default_difficulty: int = 1
    max_episodes: int = 1000
    seed: int | None = None
