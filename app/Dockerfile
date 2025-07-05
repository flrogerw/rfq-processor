FROM python:3.11-slim

WORKDIR /app

RUN apt update
RUN apt install -y build-essential python3-dev postgresql-client

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]