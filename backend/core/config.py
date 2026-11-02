from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    workspace_dir: Path = Path("./data/repos")   # cloned repos + index files live here
    max_index_workers: int = 2                   # max concurrent indexing jobs
    clone_timeout_s: int = 300
    supported_extensions: tuple[str, ...] = (".py",)
    max_file_bytes: int = 500_000                # skip huge/generated files


settings = Settings()