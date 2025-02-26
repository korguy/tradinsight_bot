FROM python:3.10-slim-buster

&& apt-get install -y --no-install-recommends \
    build-essential \  # For compiling (gcc, make, etc.)
    wget \           # For downloading ta-lib
    tar \            # For extracting ta-lib
    autoconf \       # For generating configure scripts
    automake \       # For generating configure scripts
    libtool \        # For managing shared libraries
    && apt-get update && apt-get install -y --no-install-recommends \
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