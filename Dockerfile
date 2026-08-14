FROM python:3.12-slim

ENV TZ=America/Sao_Paulo
RUN apt-get update \
    && apt-get install -y --no-install-recommends cron tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY cfc_orcamento.py .
COPY crontab /etc/cron.d/cfc-orcamento
RUN chmod 0644 /etc/cron.d/cfc-orcamento && crontab /etc/cron.d/cfc-orcamento

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
