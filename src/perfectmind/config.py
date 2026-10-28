from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LACUNA_", env_file=".env", extra="ignore", frozen=True
    )

    request_timeout: float = 30.0
    log_level: str = "INFO"

    base_url: str = "https://cityofmarkham.perfectmind.com"
    dropin_widget_id: str = "6825ea71-e5b7-4c2a-948f-9195507ad90a"
    user_agent: str = "perfectmind-claude-plugin/0.1 (+https://github.com/lacuna-core)"


SETTINGS = Settings()
