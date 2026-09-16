from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    database_url: str = "sqlite:///./data/app.db"
    upload_dir: str = "./data/uploads"
    max_upload_size: int = 50 * 1024 * 1024  # 50MB
    # 用字符串承载，避免 pydantic-settings 对 list[str] 强制 JSON 解析。
    # 多个来源用逗号分隔，通过 cors_origins_list 读取。
    cors_origins: str = "http://localhost:5173,http://localhost:4173"

    # AI
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-sonnet-20241022"
    glm_api_key: str = ""
    glm_base_url: str = "https://open.bigmodel.cn/api/paas/v4"
    glm_model: str = "glm-5.3"
    glm_flash_model: str = "glm-5.3-flash"

    # Email
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_tls: bool = True

        @property
    def cors_origins_list(self) -> list[str]:
        """把逗号分隔的 CORS_ORIGINS 展开成列表。"""
        return [o.strip() for o in str(self.cors_origins).split(",") if o.strip()]



settings = Settings()
