FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV VIRTUAL_ENV=/opt/kohakuhub-venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install uv
RUN pip install --no-cache-dir uv

WORKDIR /app

COPY ./pyproject.toml .
COPY ./README.md .
RUN mkdir -p /app/src/kohakuhub
RUN echo "" > /app/src/kohakuhub/__init__.py
RUN uv venv "$VIRTUAL_ENV" && uv pip install -e .

COPY ./src/kohakuhub ./src/kohakuhub
COPY ./scripts ./scripts
COPY ./docker/startup.py /app/startup.py
RUN chmod +x /app/startup.py

EXPOSE 48888
CMD ["/app/startup.py"]
