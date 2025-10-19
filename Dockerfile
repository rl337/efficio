# Use Python 3.12 as base image
FROM python:3.12-slim

# Install system dependencies required for CadQuery and OpenCASCADE
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libgl1-mesa-dev \
    libglu1-mesa-dev \
    libxrender1 \
    libxext6 \
    libx11-6 \
    libxrandr2 \
    libxss1 \
    libxcursor1 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxi6 \
    libxtst6 \
    libnss3 \
    libasound2 \
    libfontconfig1 \
    libfreetype6 \
    libcairo2-dev \
    libpango1.0-dev \
    libgdk-pixbuf-xlib-2.0-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy poetry files and README
COPY pyproject.toml poetry.lock README.md ./

# Install Poetry
RUN pip install poetry

# Configure Poetry
RUN poetry config virtualenvs.create false

# Install dependencies (without current project)
RUN poetry install --only=main --no-root

# Copy source code
COPY . .

# Install the package in development mode
RUN poetry install

# Set environment variables
ENV PYTHONPATH=/app
ENV DISPLAY=:99

# Default command
CMD ["poetry", "run", "python", "-m", "efficio", "--help"]
