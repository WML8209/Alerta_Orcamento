#!/bin/sh
set -e

# Cron não herda as variáveis de ambiente do container, então salvamos as
# variáveis SMTP_*/EMAIL_* recebidas via `docker run --env-file` num arquivo que o
# job do cron carrega antes de rodar o script.
# Os valores vão entre aspas simples (senhas podem conter espaços/símbolos).
printenv | grep -E '^(SMTP_|EMAIL_)' \
  | sed "s/'/'\\\\''/g; s/^\([^=]*\)=\(.*\)$/export \1='\2'/" > /app/env.sh

touch /var/log/cron.log
cron
tail -f /var/log/cron.log
