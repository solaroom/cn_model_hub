FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/opt/cn_model_hub-venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-client \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install --no-cache-dir uv

WORKDIR /app

COPY ./pyproject.toml .
COPY ./README.md .
RUN mkdir -p /app/src/cn_model_hub
RUN echo "" > /app/src/cn_model_hub/__init__.py
RUN uv venv --seed "$VIRTUAL_ENV" \
    && uv pip install \
        --index-url https://download.pytorch.org/whl/cpu \
        torch \
    && uv pip install -e ".[assistant]"
RUN python - <<'PY'
from modelscope.hub.snapshot_download import snapshot_download

snapshot_download("AI-ModelScope/bge-small-zh-v1.5", cache_dir="/models/modelscope")
PY

COPY ./src/cn_model_hub ./src/cn_model_hub
COPY ./scripts ./scripts
COPY ./docs ./docs
COPY ./examples/datasets/c-eval/quick_eval ./examples/datasets/c-eval/quick_eval
COPY ./docker/startup.py /app/startup.py
RUN chmod +x /app/startup.py

EXPOSE 48888
CMD ["/app/startup.py"]
