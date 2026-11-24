from typing import Literal, Self
from urllib.parse import urlparse

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

TAMANHO_MINIMO_SECRET_KEY = 32


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )

    AMBIENTE: Literal["desenvolvimento", "producao"] = "producao"
    PROXIES_CONFIAVEIS: list[str] = []

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
    TOTP_EMISSOR: str = "Balancia"
    DESAFIO_2FA_MIN: int = 5

    SMTP_HOST: str = "localhost"
    SMTP_PORTA: int = 587
    SMTP_SEGURANCA: Literal["starttls", "ssl", "nenhuma"] = "starttls"
    SMTP_USUARIO: str = ""
    SMTP_SENHA: str = ""
    SMTP_TIMEOUT_S: int = 10
    EMAIL_REMETENTE: str = "Balancia <nao-responda@localhost>"

    FRONT_URL: str = "http://localhost:5500"
    TOKEN_VERIFICACAO_HORAS: int = 24
    TOKEN_REDEFINIR_SENHA_MIN: int = 30
    TOKEN_TROCAR_EMAIL_MIN: int = 60
    TOKEN_INTERVALO_ENVIO_MIN: int = 2

    LEMBRETES_INTERVALO_MIN: int = 15
    LEMBRETES_HORA: int = 8
    NOTIFICACOES_RETENCAO_DIAS: int = 90

    SECRET_KEY: str
    TOTP_CHAVE: str
    CORS_ORIGINS: list[str] = []

    @model_validator(mode="after")
    def validar_producao(self) -> Self:
        if self.AMBIENTE != "producao":
            return self

        problemas = []
        if not self.COOKIE_SECURE:
            problemas.append("COOKIE_SECURE precisa ser true")
        if len(self.SECRET_KEY) < TAMANHO_MINIMO_SECRET_KEY or self.SECRET_KEY.startswith("troque"):
            problemas.append(f"SECRET_KEY precisa ser aleatória e ter ao menos {TAMANHO_MINIMO_SECRET_KEY} caracteres")
        if self.SMTP_SEGURANCA == "nenhuma":
            problemas.append("SMTP_SEGURANCA não pode ser nenhuma")
        if urlparse(self.FRONT_URL).scheme != "https":
            problemas.append("FRONT_URL precisa usar https")
        for origem in self.CORS_ORIGINS:
            endereco = urlparse(origem)
            if origem == "*" or (endereco.scheme != "https" and endereco.hostname != "localhost"):
                problemas.append(f"CORS_ORIGINS não aceita {origem!r} em produção")

        if problemas:
            raise ValueError("Configuração insegura para produção: " + "; ".join(problemas))
        return self


settings = Settings()