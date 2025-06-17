FROM python:3.11-slim

WORKDIR /app

# Install OS packages for Playwright dependencies
RUN apt-get update && apt-get install -y wget gnupg curl unzip \
    ca-certificates fonts-liberation libasound2 libatk-bridge2.0-0 \
    libatk1.0-0 libcups2 libdbus-1-3 libgdk-pixbuf2.0-0 libnspr4 \
    libnss3 libxcomposite1 libxdamage1 libxrandr2 xdg-utils \
    libu2f-udev libvulkan1 libxss1 libappindicator3-1 libgbm1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Install Playwright + its browsers
RUN pip install playwright && playwright install --with-deps

COPY . .

CMD ["python", "bot.py"]
