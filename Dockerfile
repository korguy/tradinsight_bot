FROM python:3.10-slim-buster

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \  # For compiling
    software-properties-common \ # Needed for add-apt-repository
    libtool \ # Needed for ta-lib
    automake \ # Needed for ta-lib
    && add-apt-repository universe \  # Add the universe repository (if needed)
    && apt-get update && apt-get install -y --no-install-recommends \
    libta-lib-dev \ # Install the dev package
    && rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/ta-lib/ta-lib/releases/download/v0.6.4/ta-lib-0.6.4-src.tar.gz && \
  tar -xzf ta-lib-0.6.4-src.tar.gz && \
  cd ta-lib-0.6.4 && \
  ./configure --prefix=/usr && \
  make && \
  make install

RUN pip install --no-cache-dir -r requirements.txt # Or use your preferred method for installing python packages

COPY . .

CMD ["python", "main.py"]