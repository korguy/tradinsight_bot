FROM python:3.10-slim-buster

RUN apt-get update

RUN wget https://github.com/ta-lib/ta-lib/releases/download/v0.6.4/ta-lib-0.6.4-src.tar.gz && \
  tar -xzf ta-lib-0.6.4-src.tar.gz && \
  cd ta-lib-0.6.4 && \
  ./configure --prefix=/usr && \
  make && \
  make install

RUN pip install --no-cache-dir -r requirements.txt # Or use your preferred method for installing python packages

COPY . .

CMD ["python", "main.py"]