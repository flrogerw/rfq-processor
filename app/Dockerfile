FROM python:3.11-slim

# Set working directory
WORKDIR /app

RUN apt update
RUN apt install -y build-essential python3-dev postgresql-client
# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/entrypoint.sh
RUN chmod +x /app/main.py

ENTRYPOINT ["/app/entrypoint.sh"]