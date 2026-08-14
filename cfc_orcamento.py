#!/usr/bin/env python3
"""Cliente para a API de Dados Abertos do Orçamento do CFC, com alerta via WhatsApp
(Z-API) quando o valor realizado se aproxima do orçado.

Variáveis de ambiente necessárias para o alerta:
    ZAPI_INSTANCE_ID   - ID da instância Z-API
    ZAPI_TOKEN         - Token da instância Z-API
    ZAPI_CLIENT_TOKEN  - (opcional) Client-Token de segurança da conta Z-API
    ZAPI_TO            - Número(s) destino, separados por vírgula, sem "+" e sem espaços
                          ex: 5561999999999,5511988888888
"""

import argparse
import json
import os
import sys

import requests

API_URL = "https://www3.cfc.org.br/spw/API_SPW/dadosAbertos/orcamento"
ZAPI_URL_TEMPLATE = "https://api.z-api.io/instances/{instance}/token/{token}/send-text"

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


def enviar_whatsapp(mensagem: str) -> None:
    """Envia uma mensagem via Z-API para um ou mais destinatários."""
    instance = os.environ["ZAPI_INSTANCE_ID"]
    token = os.environ["ZAPI_TOKEN"]
    client_token = os.environ.get("ZAPI_CLIENT_TOKEN", "").strip()
    destinatarios = [d.strip() for d in os.environ["ZAPI_TO"].split(",") if d.strip()]

    headers = {"Client-Token": client_token} if client_token else {}

    for destinatario in destinatarios:
        resp = requests.post(
            ZAPI_URL_TEMPLATE.format(instance=instance, token=token),
            headers=headers,
            json={"phone": destinatario, "message": mensagem},
            timeout=30,
        )
        resp.raise_for_status()


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
    parser.add_argument("--alertar", action="store_true", help="Envia alerta via WhatsApp quando houver contas no limite")
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
            enviar_whatsapp(mensagem)
            print(f"Alerta enviado via WhatsApp para {len(alertas)} conta(s).", file=sys.stderr)
        else:
            print("Nenhuma conta dentro do limite de alerta.", file=sys.stderr)


if __name__ == "__main__":
    main()
