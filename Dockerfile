FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt constraints.txt ./
RUN pip install --no-cache-dir -r requirements.txt -c constraints.txt

COPY . .
ENV PYPHI_WELCOME_OFF=true PYTHONUNBUFFERED=1

CMD ["python", "-m", "org_frontier.classifier.validate"]
