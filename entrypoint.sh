#!/bin/sh
set -e

# Cron não herda as variáveis de ambiente do container, então salvamos as
# variáveis ZAPI_* recebidas via `docker run --env-file` num arquivo que o
# job do cron carrega antes de rodar o script.
printenv | grep -E '^ZAPI_' | sed 's/^\(.*\)$/export \1/' > /app/env.sh

touch /var/log/cron.log
cron
tail -f /var/log/cron.log
