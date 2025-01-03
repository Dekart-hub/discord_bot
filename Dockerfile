FROM python:3.11

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    python3-dev \
    libffi-dev \
    libopus-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install PyNaCl

COPY . .

CMD ["python", "main.py"]
