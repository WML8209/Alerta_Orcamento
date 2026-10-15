#!/usr/bin/env python3
"""Cliente para a API de Dados Abertos do Orçamento do CFC, com alerta por e-mail
(SMTP) quando o valor realizado se aproxima do orçado.

Variáveis de ambiente necessárias para o alerta:
    SMTP_HOST      - Servidor SMTP (ex: smtp.gmail.com)
    SMTP_PORT      - (opcional) Porta SMTP (padrão: 587 com STARTTLS; 465 usa SSL)
    SMTP_USER      - Usuário de autenticação SMTP
    SMTP_PASSWORD  - Senha (ou senha de app) SMTP
    EMAIL_FROM     - (opcional) Remetente (padrão: SMTP_USER)
    EMAIL_TO       - Destinatário(s), separados por vírgula
                      ex: fulano@exemplo.com,ciclano@exemplo.com
"""

import argparse
import json
import os
import smtplib
import sys
from email.message import EmailMessage

import requests

API_URL = "https://www3.cfc.org.br/spw/API_SPW/dadosAbertos/orcamento"

CONTAS_PADRAO = [
    "6.3.1.3.02.03.001",
    "6.3.1.3.02.03.002",
    "6.3.1.3.02.03.003",
    "6.3.1.3.02.04.001",
    "6.3.1.3.02.04.002",
    "6.3.1.3.02.04.003",
    "6.3.1.3.02.06.001",
]

LIMITE_ALERTA_PADRAO = 100_000.0  # R$ de folga restante que dispara o alerta


def buscar_orcamento(ano: int, conselho: str = "CFC") -> list[dict]:
    """Busca as linhas do orçamento de um ano/conselho."""
    resp = requests.get(
        API_URL,
        headers={"conselho": conselho, "ano": str(ano)},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def filtrar_contas(linhas: list[dict], contas: list[str]) -> list[dict]:
    """Filtra linhas pela conta orçamentária."""
    contas_set = set(contas)
    return [l for l in linhas if l.get("codigoConta") in contas_set]


def parse_valor_brl(valor: str) -> float:
    """Converte string no formato brasileiro (1.234,56) para float."""
    return float(valor.replace(".", "").replace(",", "."))


def verificar_alertas(linhas: list[dict], limite: float) -> list[dict]:
    """Retorna as linhas cuja folga (orçado - realizado) é menor que o limite."""
    alertas = []
    for l in linhas:
        orcado = parse_valor_brl(l["valorOrcado"])
        realizado = parse_valor_brl(l["valorRealizado"])
        folga = orcado - realizado
        if folga < limite:
            alertas.append({**l, "folga": folga})
    return alertas


def enviar_email(assunto: str, mensagem: str) -> None:
    """Envia o alerta por e-mail via SMTP para um ou mais destinatários."""
    host = os.environ["SMTP_HOST"].strip()
    porta = int(os.environ.get("SMTP_PORT", "587"))
    usuario = os.environ["SMTP_USER"].strip()
    senha = os.environ["SMTP_PASSWORD"].strip()
    remetente = os.environ.get("EMAIL_FROM", "").strip() or usuario
    destinatarios = [d.strip() for d in os.environ["EMAIL_TO"].split(",") if d.strip()]

    msg = EmailMessage()
    msg["Subject"] = assunto
    msg["From"] = remetente
    msg["To"] = ", ".join(destinatarios)
    msg.set_content(mensagem)

    if porta == 465:
        with smtplib.SMTP_SSL(host, porta, timeout=30) as smtp:
            smtp.login(usuario, senha)
            smtp.send_message(msg)
    else:
        with smtplib.SMTP(host, porta, timeout=30) as smtp:
            smtp.starttls()
            smtp.login(usuario, senha)
            smtp.send_message(msg)


def formatar_valor_brl(valor: float) -> str:
    """Converte float para string no formato brasileiro (1.234,56)."""
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def montar_mensagem_alerta(alertas: list[dict], ano: int) -> str:
    linhas = [f"⚠️ Alerta orçamentário CFC {ano} — contas próximas do limite:"]
    for a in alertas:
        linhas.append(
            f"- {a['codigoConta']} ({a['descricaoConta']}): "
            f"orçado R$ {a['valorOrcado']}, realizado R$ {a['valorRealizado']}, "
            f"folga R$ {formatar_valor_brl(a['folga'])}"
        )
    return "\n".join(linhas)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("ano", type=int, nargs="?", default=2026, help="Ano do orçamento (padrão: 2026)")
    parser.add_argument("--conselho", default="CFC", help="Sigla do conselho (padrão: CFC)")
    parser.add_argument(
        "--contas",
        nargs="+",
        default=CONTAS_PADRAO,
        help="Lista de contas orçamentárias a filtrar (padrão: contas pré-definidas)",
    )
    parser.add_argument(
        "--limite-alerta",
        type=float,
        default=LIMITE_ALERTA_PADRAO,
        help=f"Folga (R$) abaixo da qual dispara alerta (padrão: {LIMITE_ALERTA_PADRAO:,.2f})",
    )
    parser.add_argument("--alertar", action="store_true", help="Envia alerta por e-mail quando houver contas no limite")
    parser.add_argument("-o", "--output", help="Arquivo de saída (padrão: stdout)")
    args = parser.parse_args()

    linhas = buscar_orcamento(args.ano, args.conselho)
    linhas = filtrar_contas(linhas, args.contas)

    saida = json.dumps(linhas, indent=2, ensure_ascii=False)
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(saida)
        print(f"{len(linhas)} linhas salvas em {args.output}", file=sys.stderr)
    else:
        print(saida)

    if args.alertar:
        alertas = verificar_alertas(linhas, args.limite_alerta)
        if alertas:
            mensagem = montar_mensagem_alerta(alertas, args.ano)
            enviar_email(f"Alerta orçamentário CFC {args.ano}", mensagem)
            print(f"Alerta enviado por e-mail para {len(alertas)} conta(s).", file=sys.stderr)
        else:
            print("Nenhuma conta dentro do limite de alerta.", file=sys.stderr)


if __name__ == "__main__":
    main()
