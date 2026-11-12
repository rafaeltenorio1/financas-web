from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    COOKIE_SECURE: bool = True  
    SESSAO_DURACAO_DIAS: int = 7  
    SESSAO_INATIVIDADE_MIN: int = 30  
    LOGIN_MAX_FALHAS: int = 5 
    LOGIN_JANELA_MIN: int = 15  
    LOGIN_MAX_FALHAS_IP: int = 20


settings = Settings()