FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    wget curl unzip gnupg \
    libnss3 libxss1 libappindicator1 \
    fonts-liberation libatk-bridge2.0-0 libgtk-3-0 \
    libasound2 libgbm-dev libxshmfence1 \
    chromium chromium-driver \
    && rm -rf /var/lib/apt/lists/*

ENV CHROME_BIN=/usr/bin/chromium
ENV PATH="/usr/lib/chromium:$PATH"

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "main.py"]
