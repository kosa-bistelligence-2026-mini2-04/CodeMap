FROM python:3.13

RUN pip install uv

WORKDIR /app

RUN mkdir -p /app/temp/git && \
    chmod -R 777 /app/temp && \
    ls -la /app/temp  # Verify permissions

RUN git config --global --add safe.directory '*' && \
    git config --global core.askpass true

COPY pyproject.toml uv.lock ./

RUN uv sync

COPY src/ src/

ENV ENV=production
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV TMPDIR=/app/temp
ENV GITINGEST_TEMP_DIR=/app/temp/git
ENV GIT_TERMINAL_PROMPT=0
ENV GIT_ASKPASS=/bin/echo
ENV GIT_CONFIG_NOSYSTEM=1
ENV GIT_DISCOVERY_ACROSS_FILESYSTEM=1
ENV PORT=8080

RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app

USER appuser

RUN which git && git --version

EXPOSE ${PORT}

CMD ["sh", "-c", "uvicorn src.main:app --host 0.0.0.0 --port ${PORT}"]