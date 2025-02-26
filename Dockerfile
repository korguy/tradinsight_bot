FROM python:3.10-slim-buster
RUN apt-get update && apt-get install -y --no-install-recommends \
    libta-lib-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt .  # Or copy your pyproject.toml and related files
RUN pip install --no-cache-dir -r requirements.txt # Or use your preferred method for installing python packages
COPY . .
CMD ["python", "main.py"]