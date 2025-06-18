FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    wget curl unzip gnupg \
    libnss3 libxss1 libatk-bridge2.0-0 libgtk-3-0 \
    libasound2 libgbm-dev libxshmfence1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright dependencies and browsers
RUN python -m playwright install --with-deps

COPY . .

CMD ["python", "main.py"]
