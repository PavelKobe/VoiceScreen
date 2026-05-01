from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://voicescreen:devpassword@localhost:5432/voicescreen"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Yandex SpeechKit
    yandex_cloud_api_key: str = ""
    yandex_cloud_folder_id: str = ""

    # LLM (OpenRouter)
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    openrouter_model: str = "openai/gpt-4o-mini"

    # Telegram
    telegram_bot_token: str = ""

    # Voximplant
    voximplant_account_id: str = ""
    voximplant_api_key: str = ""
    voximplant_application_id: str = ""
    voximplant_application_name: str = ""
    voximplant_rule_id: str = ""
    voximplant_from_number: str = ""

    # Yandex Object Storage
    yos_access_key: str = ""
    yos_secret_key: str = ""
    yos_bucket: str = "voicescreen-recordings"
    yos_endpoint: str = "https://storage.yandexcloud.net"

    # App
    app_env: str = "development"
    admin_api_key: str = ""
    log_level: str = "debug"
    # Public WS URL for VoxEngine to connect back to us (wss://host/api/v1/ws/call)
    public_ws_url: str = ""
    # Shared secret used by VoxEngine → backend to authorize the WS session.
    # Empty value disables auth (for local dev only).
    ws_auth_token: str = ""

    # Dispatch / scheduler
    call_timezone: str = "Europe/Moscow"
    call_window_start_hour: int = 9
    call_window_end_hour: int = 21
    call_max_attempts: int = 3
    call_retry_backoff_minutes: list[int] = [30, 120, 360]

    # SMTP (HR-уведомления по итогам звонка). Yandex 360: smtp.yandex.ru:465 SSL.
    smtp_host: str = "smtp.yandex.ru"
    smtp_port: int = 465
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@voxscreen.ru"
    smtp_use_ssl: bool = True
    # Базовый URL веб-кабинета — используется в письмах для ссылки на CallDetail.
    web_app_base_url: str = "https://app.voxscreen.ru"

    # SMS-предупреждение кандидата идёт через Voximplant SendSmsMessage —
    # с того же номера voximplant_from_number, с которого мы звоним.
    # Отдельных секретов не нужно: используем уже настроенные
    # voximplant_account_id / voximplant_api_key.

    # Web session auth (SPA на app.voxscreen.ru)
    secret_key: str = ""  # SessionMiddleware HMAC; пустое значение => session-auth отключён
    cookie_domain: str = ".voxscreen.ru"
    cookie_secure: bool = True
    cors_origins: list[str] = ["https://app.voxscreen.ru"]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
