FROM python:3.15-slim
COPY --from=ghcr.io/astral-sh/uv:0.13.9 /uv /usr/local/bin/uv

ARG UID=1000
ARG GID=1000
RUN groupadd --gid "${GID}" app && useradd --uid "${UID}" --gid "${GID}" --create-home app

ENV UV_PYTHON_DOWNLOADS=never
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY --chown=app:app . .

USER app
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--no-proxy-headers"]
