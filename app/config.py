from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://voicescreen:devpassword@localhost:5432/voicescreen"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Yandex SpeechKit
    yandex_cloud_api_key: str = ""
    yandex_cloud_folder_id: str = ""

    # LLM
    openai_api_key: str = ""
    yandex_gpt_api_key: str = ""
    yandex_gpt_folder_id: str = ""

    # Telegram
    telegram_bot_token: str = ""

    # Mango Office
    mango_api_key: str = ""
    mango_api_secret: str = ""
    mango_from_number: str = ""

    # Yandex Object Storage
    yos_access_key: str = ""
    yos_secret_key: str = ""
    yos_bucket: str = "voicescreen-recordings"
    yos_endpoint: str = "https://storage.yandexcloud.net"

    # App
    app_env: str = "development"
    log_level: str = "debug"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
