# Stage 1: Build Stage
FROM python:3.12-slim-bookworm AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Set environment variables for uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

# Set the working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies without installing the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Copy the application source code
COPY . .

# Install the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Stage 2: Runtime Stage
FROM python:3.12-slim-bookworm

# Set the working directory
WORKDIR /app

# Copy the application and its virtual environment from the builder stage
COPY --from=builder /app /app

# Ensure the virtual environment's binaries are in the PATH
ENV PATH="/app/.venv/bin:$PATH"

ENV PORT=3003
ENV LISTEN="0.0.0.0" 
ENV ENTRZ_EMAIL="not@set.com"
ENV LOGLEVEL="info"

# Expose the application port (adjust as needed)
EXPOSE ${PORT}

# Set the entry point for the container
CMD ["sh", "-c", "uvicorn main:app --host ${LISTEN} --port ${PORT}"]
