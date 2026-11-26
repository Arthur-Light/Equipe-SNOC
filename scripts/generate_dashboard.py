#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de extração do Dashboard BI SNOC 2026.
Utiliza a JQL exata consolidada do board, com paginação robusta,
autenticação segura e mapeamento automático dos 21 colaboradores.
"""

import os
import sys
import json
import re
from datetime import datetime, timezone, timedelta
import requests
from requests.auth import HTTPBasicAuth

BRT = timezone(timedelta(hours=-3))

JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "https://grupolight.atlassian.net").rstrip("/")
JIRA_USER_EMAIL = os.getenv("JIRA_USER_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

if not JIRA_USER_EMAIL or not JIRA_API_TOKEN:
    print("ERRO CRÍTICO: Secrets JIRA_USER_EMAIL ou JIRA_API_TOKEN não configurados.", file=sys.stderr)
    sys.exit(1)

AUTH = HTTPBasicAuth(JIRA_USER_EMAIL.strip(), JIRA_API_TOKEN.strip())
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# ---------------------------------------------------------------------------
# 1. Cadastro dos 21 Colaboradores da Equipe SNOC
# ---------------------------------------------------------------------------
CARGOS = ["Analista", "Especialista", "Supervisor", "Governança"]

MEMBERS = [
    {"name": "Ludmilla de Souza", "cargo": 0, "adm": "2025-03-01", "acc": ["712020:5bd6dba2-40a3-46b5-a83f-cf00db09fd8b"]},
    {"name": "Alana Fontes Domingues", "cargo": 0, "adm": "2025-03-01", "acc": ["712020:655fe963-0a05-4ff8-8081-3e0bafc32cdb"]},
    {"name": "Micheline Reche Monteiro de Barros", "cargo": 0, "adm": "2025-03-01", "acc": ["712020:f583790a-8b5f-4c33-9ee6-0834d539fed5"]},
    {"name": "Isaac Magalhaes dos Santos", "cargo": 0, "adm": "2026-04-01", "acc": ["712020:f7fbde81-6bc7-4311-9ce0-7e36ea87bc0f"]},
    {"name": "Matheus Vinicius Seixas De Oliveira", "cargo": 0, "adm": "2025-03-01", "acc": ["712020:dae2d8d3-beeb-4fd5-aa1b-37f28fd677af"]},
    {"name": "Vitor Medeiros Tabelli", "cargo": 0, "adm": "2025-03-01", "acc": ["712020:adf44aaf-bf0f-4489-92e9-deaf9d4c4ff3"]},
    {"name": "Robson Fernandes dos Santos", "cargo": 0, "adm": "2025-03-01", "acc": ["712020:95dbe47c-974e-45e4-8196-e23b9bb381bc"]},
    {"name": "Kevin Guimarães Abrão", "cargo": 0, "adm": "2025-03-01", "acc": ["712020:140a052f-523f-4658-bd2b-4f8e71d27b9d"]},
    {"name": "Kevin Rodrigues dos Santos", "cargo": 0, "adm": "2026-06-01", "acc": ["712020:340e3e9a-011c-4ad6-be1d-6be2853ae88b"]},
    {"name": "Denison Alcantara Sampaio", "cargo": 0, "adm": "2026-04-01", "acc": ["712020:d4659e8f-6477-4162-8180-5ce658703edc"]},
    {"name": "Claudio Simoes", "cargo": 0, "adm": "2025-03-01", "acc": ["712020:b251d16c-6412-4110-8277-b53c362391d5"]},
    {"name": "Catia Selene Gomes Neuman", "cargo": 0, "adm": "2026-04-01", "acc": ["712020:354b19ea-d3ab-46cf-b7ab-89d2e82d093c"]},
    {"name": "Luiz Fernando do Nascimento da Silva", "cargo": 0, "adm": "2025-03-01", "acc": ["712020:783c9ee1-41c1-49eb-a13c-fcf827cff583"]},
    {"name": "Anael Ramon Batista Silva", "cargo": 0, "adm": "2026-08-01", "acc": ["6319fc7655b0a9e29f1c897c", "70121:f9748a51-787e-40f6-bf4b-a011f34c7f65"]},
    {"name": "Aline Perez Ganga", "cargo": 0, "adm": "2026-07-01", "acc": ["712020:60e8d181-77fc-4942-aba8-77448ad13bc2"]},
    {"name": "Guilherme Madeira Massimo", "cargo": 0, "adm": "2026-05-01", "acc": ["712020:f264a2b9-9d56-42b0-9b73-f383ed3727ba"]},
    {"name": "Edson Suraty De Andrade", "cargo": 0, "adm": "2026-09-01", "acc": ["712020:e82aad02-06a8-41b5-ac5f-baa93f16bd4a", "712020:5ed86317-2c80-4b93-bc79-3d39a19ba020"]},
    {"name": "Leonardo Cornelio de Souza", "cargo": 2, "adm": "2025-08-01", "acc": ["712020:80b24cd7-dd46-43c5-9e81-ba99725d53dd"]},
    {"name": "Gelson Henrique Silva Balbino", "cargo": 1, "adm": "2026-05-01", "acc": ["712020:f553e529-a76f-4a57-9300-ce146501edb2"]},
    {"name": "Hagar Cristian Geraldo Vilanova", "cargo": 3, "adm": "2026-06-01", "acc": ["712020:155007e8-ab9d-43f3-9cb5-4a023c7a8ded"]},
    {"name": "Isabelle Martins Gomes", "cargo": 1, "adm": "2025-12-01", "acc": ["712020:dd65b1ce-cc3d-4484-9f88-d48ff50a9cdf", "712020:041459b8-5343-46de-bf97-b31188015a73"]},
]

for m in MEMBERS:
    m["start"] = "2026-01-01" if m["adm"] < "2026-01-01" else m["adm"]

ACCOUNT_TO_PERSON = {}
for idx, m in enumerate(MEMBERS):
    for a in m["acc"]:
        ACCOUNT_TO_PERSON[a] = idx

# ---------------------------------------------------------------------------
# 2. Categorização de Motivo e Shift-Left
# ---------------------------------------------------------------------------
MOTIVOS = [
    "Acesso, senha e perfil",
    "Alarmes de monitoração (Spectrum/CheckMK/Zabbix)",
    "Instalação e suporte a software/aplicativos",
    "Sustentação GDIS/OFS (notas, manobras, baldes)",
    "Conectividade e rede do usuário",
    "Hardware e equipamento físico",
    "Infraestrutura física e energia de sites",
    "Atividades internas e treinamentos",
    "Outros / demandas diversas"
]

def classify_motive(summary: str) -> int:
    s = (summary or "").lower()
    if any(k in s for k in ["acionamento", "acompanhamento", "consulta de chamado", "consulta do chamado", "reunião", "treinamento", "validação técnica", "alinhamento"]):
        return 7
    if any(k in s for k in ["spectrum", "checkmk", "check mk", "zabbix", "device has stopped", "unresolved fault", "indisponivel", "indisponível", "redundante", "chassis down", "threshold exceeded", "falha de energia", "falha no concentrador", "alarme"]):
        return 1
    if any(k in s for k in ["link", "dmvpn", "4g", "5g", "vpn", "wifi", "wi-fi", "internet", "fibra", "radio", "sdh", "intermitência", "queda de conexão"]):
        return 4
    if any(k in s for k in ["senha", "reset", "login", "logon", "token", "desbloque", "bloqueio", "acesso", "perfil", "authenticator", "autenticador", "sso", "mfa", "permiss"]):
        return 0
    if any(k in s for k in ["gdis", "ofs", "wfm", "retorno de serviço", "manobra", "ocorrência", "balde", "ordem de serviço", "retorno ao gdis"]):
        return 3
    if any(k in s for k in ["instala", "software", "aplicativo", "outlook", "teams", "office", "excel", "sap", "genesys", "spi", "antivírus"]):
        return 2
    if any(k in s for k in ["mouse", "teclado", "monitor", "desktop", "notebook", "impressora", "toner", "totem", "cabo", "computador", "periférico"]):
        return 5
    if any(k in s for k in ["subestação", "repetidora", "nobreak", "ar condicionado", "gerador", "painel elétrico"]):
        return 6
    return 8

def classify_tier(motive_idx: int, queue_name: str) -> int:
    if "SNOC" in (queue_name or "").upper():
        return 3
    if motive_idx in [0, 1]:
        return 0
    elif motive_idx in [2, 3, 4]:
        return 1
    else:
        return 2

# ---------------------------------------------------------------------------
# 3. Consulta ao Jira utilizando a JQL Consolidada do Board
# ---------------------------------------------------------------------------
def fetch_all():
    # Monta os blocos de corte de admissão
    by_start = {}
    for idx, m in enumerate(MEMBERS):
        s = m["start"]
        by_start.setdefault(s, []).extend(m["acc"])

    clauses = []
    for s_date, accs in sorted(by_start.items()):
        acc_str = ", ".join(f'"{a}"' for a in accs)
        clauses.append(f'(assignee WAS IN ({acc_str}) AND created >= "{s_date}")')

    consolidated_jql = "(" + " OR ".join(clauses) + ") ORDER BY created DESC"

    fields = [
        "key", "summary", "issuetype", "priority", "status",
        "created", "resolutiondate", "customfield_12014", "assignee"
    ]

    url = f"{JIRA_BASE_URL}/rest/api/3/search"
    start_at = 0
    max_results = 100
    
    issue_dict = {}
    
    print(f"Conectando ao Jira em {JIRA_BASE_URL} com o usuário: {JIRA_USER_EMAIL}...")
    
    while True:
        payload = {
            "jql": consolidated_jql,
            "startAt": start_at,
            "maxResults": max_results,
            "fields": fields
        }
        res = requests.post(url, auth=AUTH, headers=HEADERS, json=payload, timeout=60)
        
        if res.status_code != 200:
            print(f"ERRO FATAL da API Jira (Status {res.status_code}): {res.text}", file=sys.stderr)
            sys.exit(1)

        data = res.json()
        issues = data.get("issues", [])
        total = data.get("total", 0)

        if not issues:
            break

        for it in issues:
            issue_dict[it["key"]] = it

        start_at += len(issues)
        print(f"  Coletados {start_at} de {total} chamados...")
        
        if start_at >= total:
            break

    # Mapeamento de atribuição dos colaboradores
    # Busca individualmente as chaves por colaborador para garantir 100% dos pares exatos
    pairs_set = set()
    print("\nMapeando atendimento por colaborador...")
    for idx, m in enumerate(MEMBERS):
        accs = ", ".join(f'"{a}"' for a in m["acc"])
        s_date = m["start"]
        p_jql = f'assignee WAS IN ({accs}) AND created >= "{s_date}"'
        
        p_start = 0
        p_total_count = 0
        while True:
            p_payload = {
                "jql": p_jql,
                "startAt": p_start,
                "maxResults": 100,
                "fields": ["key"]
            }
            p_res = requests.post(url, auth=AUTH, headers=HEADERS, json=p_payload, timeout=60)
            if p_res.status_code != 200:
                break
            p_data = p_res.json()
            p_issues = p_data.get("issues", [])
            if not p_issues:
                break
            for pit in p_issues:
                pk = pit["key"]
                if pk in issue_dict:
                    pairs_set.add((pk, idx))
            p_start += len(p_issues)
            p_total_count += len(p_issues)
            if p_start >= p_data.get("total", 0):
                break
        print(f"  [{idx+1}/21] {m['name']}: {p_total_count} chamados associados.")

    return issue_dict, pairs_set

# ---------------------------------------------------------------------------
# 4. Estruturação do Objeto DATA
# ---------------------------------------------------------------------------
def build_payload(issue_dict, pairs_set):
    prj_list = []
    q_list = ["SNOC", "(Sem Fila Equipe)"]
    t_list = []
    st_list = []
    type_ids = {}

    rows = []
    key_to_row_idx = {}

    sorted_keys = sorted(issue_dict.keys(), reverse=True)

    for k in sorted_keys:
        it = issue_dict[k]
        f = it.get("fields", {})

        parts = k.split("-")
        prj = parts[0]
        num = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0

        if prj not in prj_list:
            prj_list.append(prj)
        prj_idx = prj_list.index(prj)

        summary = f.get("summary", "")

        t_obj = f.get("issuetype") or {}
        t_name = t_obj.get("name", "Outros")
        t_id = t_obj.get("id")
        if t_name not in t_list:
            t_list.append(t_name)
        t_idx = t_list.index(t_name)
        if t_id:
            type_ids.setdefault(t_name, []).append(t_id)

        q_name = f.get("customfield_12014") or "(Sem Fila Equipe)"
        if q_name not in q_list:
            q_list.append(q_name)
        q_idx = q_list.index(q_name)

        st_name = (f.get("status") or {}).get("name", "Aberto")
        if st_name not in st_list:
            st_list.append(st_name)
        st_idx = st_list.index(st_name)

        m_idx = classify_motive(summary)
        tier_idx = classify_tier(m_idx, q_name)

        c_raw = f.get("created", "")
        c_month = int(c_raw[5:7]) if len(c_raw) >= 7 else 1
        c_int = int(c_raw[:10].replace("-", "")) if len(c_raw) >= 10 else 20260101

        r_raw = f.get("resolutiondate")
        if r_raw:
            r_month = int(r_raw[5:7])
            r_int = int(r_raw[:10].replace("-", ""))
            is_done = 1
        else:
            r_month = 13
            r_int = 0
            is_done = 0

        row = [
            prj_idx, num, summary, t_idx, q_idx, st_idx,
            m_idx, tier_idx, c_month, r_month, c_int, r_int, is_done
        ]
        key_to_row_idx[k] = len(rows)
        rows.append(row)

    pairs = []
    for k, p_idx in pairs_set:
        if k in key_to_row_idx:
            pairs.extend([key_to_row_idx[k], p_idx])

    now_brt = datetime.now(BRT)
    extract_str = now_brt.strftime("%d/%m/%Y")

    payload = {
        "cargo": CARGOS,
        "pc": [m["cargo"] for m in MEMBERS],
        "adm": [m["adm"] for m in MEMBERS],
        "start": [m["start"] for m in MEMBERS],
        "prj": prj_list,
        "q": q_list,
        "t": t_list,
        "st": st_list,
        "m": MOTIVOS,
        "tier": ["Quick Wins", "Médio Prazo", "Manter Especialistas", "Fila SNOC"],
        "p": [m["name"] for m in MEMBERS],
        "acc": [m["acc"] for m in MEMBERS],
        "typeIds": {k: list(set(v)) for k, v in type_ids.items()},
        "rows": rows,
        "pairs": pairs,
        "extract": extract_str
    }
    return payload

# ---------------------------------------------------------------------------
# 5. Injeção no HTML
# ---------------------------------------------------------------------------
def generate_html(payload, template_path="template/index_template.html", output_path="public/index.html"):
    if not os.path.exists(template_path):
        print(f"ERRO: Template não encontrado em '{template_path}'.", file=sys.stderr)
        sys.exit(1)

    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    data_json = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    pattern = r"const DATA = \{.*?\};"
    replacement = f"const DATA = {data_json};"

    if re.search(pattern, content, flags=re.DOTALL):
        new_content = re.sub(pattern, replacement, content, count=1, flags=re.DOTALL)
    else:
        new_content = content.replace("__DATA_JSON__", f"const DATA = {data_json};")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"\n==========================================")
    print(f"Sucesso! Painel gerado com sucesso.")
    print(f"Total de chamados únicos: {len(payload['rows'])}")
    print(f"Total de atendimentos: {len(payload['pairs']) // 2}")
    print(f"Data de referência da extração: {payload['extract']}")
    print(f"==========================================\n")

def main():
    issue_dict, pairs_set = fetch_all()
    payload = build_payload(issue_dict, pairs_set)
    generate_html(payload)

if __name__ == "__main__":
    main()
