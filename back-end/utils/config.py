from typing import Literal

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
    SESSAO_LEMBRAR_DURACAO_DIAS: int = 90
    SESSAO_LEMBRAR_INATIVIDADE_DIAS: int = 30
    LOGIN_MAX_FALHAS: int = 5 
    LOGIN_JANELA_MIN: int = 15  
    LOGIN_MAX_FALHAS_IP: int = 20
    LIMPEZA_INTERVALO_MIN: int = 60
    TENTATIVAS_RETENCAO_DIAS: int = 30
    TOTP_EMISSOR: str = "Finanças"
    DESAFIO_2FA_MIN: int = 5

    SMTP_HOST: str = "localhost"
    SMTP_PORTA: int = 587
    SMTP_SEGURANCA: Literal["starttls", "ssl", "nenhuma"] = "starttls"
    SMTP_USUARIO: str = ""
    SMTP_SENHA: str = ""
    SMTP_TIMEOUT_S: int = 10
    EMAIL_REMETENTE: str = "Finanças <nao-responda@localhost>"

    SECRET_KEY: str
    TOTP_CHAVE: str
    CORS_ORIGINS: list[str] = []


settings = Settings()