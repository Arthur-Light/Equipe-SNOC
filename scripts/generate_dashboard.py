#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script de atualização do Dashboard BI SNOC 2026.
Consulta a API REST do Jira Cloud da Light via JQL, aplica as regras de corte por
admissão dos 21 colaboradores, classifica os motivos e a Matriz Shift-Left,
monta a estrutura de dados compacta e injeta diretamente no HTML final.
"""

import os
import sys
import json
import re
from datetime import datetime, timezone, timedelta
import requests
from requests.auth import HTTPBasicAuth

# Fuso horário de Brasília (UTC-3)
BRT = timezone(timedelta(hours=-3))

# ---------------------------------------------------------------------------
# 1. Configurações de Conexão com o Jira (lidas dos Secrets do GitHub)
# ---------------------------------------------------------------------------
JIRA_BASE_URL = os.getenv("JIRA_BASE_URL", "https://grupolight.atlassian.net").rstrip("/")
JIRA_USER_EMAIL = os.getenv("JIRA_USER_EMAIL")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

if not JIRA_USER_EMAIL or not JIRA_API_TOKEN:
    print("ERRO: Variáveis JIRA_USER_EMAIL e JIRA_API_TOKEN não foram encontradas.", file=sys.stderr)
    print("Cadastre-as em: Settings -> Secrets and variables -> Actions.", file=sys.stderr)
    sys.exit(1)

AUTH = HTTPBasicAuth(JIRA_USER_EMAIL, JIRA_API_TOKEN)
HEADERS = {
    "Accept": "application/json",
    "Content-Type": "application/json"
}

# ---------------------------------------------------------------------------
# 2. Cadastro da Equipe SNOC (Planilha 17/11/2026 - 21 colaboradores / 24 contas)
# ---------------------------------------------------------------------------
CARGOS = ["Analista", "Especialista", "Supervisor", "Governança"]

# cargo: 0=Analista, 1=Especialista, 2=Supervisor, 3=Governança
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

# Regra temporal: corte no 1º dia do mês de admissão ou 01/01/2026 (o que for mais recente)
for m in MEMBERS:
    m["start"] = "2026-01-01" if m["adm"] < "2026-01-01" else m["adm"]

ACCOUNT_TO_PERSON = {}
for idx, m in enumerate(MEMBERS):
    for a in m["acc"]:
        ACCOUNT_TO_PERSON[a] = idx

# ---------------------------------------------------------------------------
# 3. Categorização de Motivo e Tiers Shift-Left
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
    
    # 1. Atividades internas
    if any(k in s for k in ["acionamento", "acompanhamento", "consulta de chamado", "consulta do chamado", "reunião", "treinamento", "validação técnica", "alinhamento"]):
        return 7
    # 2. Alarmes de monitoração
    if any(k in s for k in ["spectrum", "checkmk", "check mk", "zabbix", "device has stopped", "unresolved fault", "indisponivel", "indisponível", "redundante", "chassis down", "threshold exceeded", "falha de energia", "falha no concentrador", "alarme"]):
        return 1
    # 3. Conectividade e rede
    if any(k in s for k in ["link", "dmvpn", "4g", "5g", "vpn", "wifi", "wi-fi", "internet", "fibra", "radio", "sdh", "intermitência", "queda de conexão"]):
        return 4
    # 4. Acesso, senha e perfil
    if any(k in s for k in ["senha", "reset", "login", "logon", "token", "desbloque", "bloqueio", "acesso", "perfil", "authenticator", "autenticador", "sso", "mfa", "permiss"]):
        return 0
    # 5. GDIS / OFS
    if any(k in s for k in ["gdis", "ofs", "wfm", "retorno de serviço", "manobra", "ocorrência", "balde", "ordem de serviço", "retorno ao gdis"]):
        return 3
    # 6. Software
    if any(k in s for k in ["instala", "software", "aplicativo", "outlook", "teams", "office", "excel", "sap", "genesys", "spi", "antivírus"]):
        return 2
    # 7. Hardware
    if any(k in s for k in ["mouse", "teclado", "monitor", "desktop", "notebook", "impressora", "toner", "totem", "cabo", "computador", "periférico"]):
        return 5
    # 8. Infraestrutura física e energia
    if any(k in s for k in ["subestação", "repetidora", "nobreak", "ar condicionado", "gerador", "painel elétrico"]):
        return 6
    
    return 8  # Outros

def classify_tier(motive_idx: int, queue_name: str) -> int:
    """
    0: Quick Wins
    1: Médio Prazo
    2: Manter nos Especialistas
    3: Fila SNOC
    """
    if "SNOC" in (queue_name or "").upper():
        return 3
    if motive_idx in [0, 1]:      # Acesso/senha e Alarmes
        return 0
    elif motive_idx in [2, 3, 4]: # Software, GDIS/OFS e Conectividade
        return 1
    else:                         # Hardware, Infraestrutura, Internas e Outros
        return 2

# ---------------------------------------------------------------------------
# 4. Consulta à API REST do Jira (com paginação automática)
# ---------------------------------------------------------------------------
def run_jql_search(jql: str, fields: list):
    url = f"{JIRA_BASE_URL}/rest/api/3/search"
    start_at = 0
    max_results = 100
    all_issues = []

    print(f"Executando JQL: {jql}")
    while True:
        payload = {
            "jql": jql,
            "startAt": start_at,
            "maxResults": max_results,
            "fields": fields,
            "expand": ["changelog"]
        }
        res = requests.post(url, auth=AUTH, headers=HEADERS, json=payload, timeout=60)
        if res.status_code != 200:
            print(f"Erro na requisição ({res.status_code}): {res.text}", file=sys.stderr)
            break
        data = res.json()
        issues = data.get("issues", [])
        if not issues:
            break
        all_issues.extend(issues)
        start_at += len(issues)
        if start_at >= data.get("total", 0):
            break
        print(f"  Coletados {start_at}/{data.get('total')}...")

    return all_issues

def fetch_data():
    """
    Busca os chamados criados desde 01/01/2026 que passaram por algum dos colaboradores,
    respeitando o corte inicial de admissão.
    """
    fields = [
        "key", "summary", "issuetype", "priority", "status",
        "created", "resolutiondate", "customfield_12014", "assignee"
    ]

    by_start = {}
    for idx, m in enumerate(MEMBERS):
        s = m["start"]
        by_start.setdefault(s, []).extend(m["acc"])

    issue_dict = {}     # key -> issue_obj
    pairs_set = set()   # (key, person_idx)

    for start_date, accs in by_start.items():
        acc_str = ", ".join(f'"{a}"' for a in accs)
        jql = (
            f"assignee WAS IN ({acc_str}) "
            f'AND created >= "{start_date}" '
            "ORDER BY created DESC"
        )
        issues = run_jql_search(jql, fields)
        
        for it in issues:
            k = it["key"]
            issue_dict[k] = it
            c_date = (it.get("fields", {}).get("created") or "")[:10]
            
            # 1. Verifica quem foi o responsável atual
            ass = it.get("fields", {}).get("assignee")
            if ass and ass.get("accountId") in ACCOUNT_TO_PERSON:
                p_idx = ACCOUNT_TO_PERSON[ass["accountId"]]
                if c_date >= MEMBERS[p_idx]["start"]:
                    pairs_set.add((k, p_idx))

            # 2. Verifica quem atuou pelo changelog (histórico)
            histories = it.get("changelog", {}).get("histories", [])
            for h in histories:
                for item in h.get("items", []):
                    if item.get("field") == "assignee":
                        from_acc = item.get("from")
                        to_acc = item.get("to")
                        for a in [from_acc, to_acc]:
                            if a in ACCOUNT_TO_PERSON:
                                p_idx = ACCOUNT_TO_PERSON[a]
                                if c_date >= MEMBERS[p_idx]["start"]:
                                    pairs_set.add((k, p_idx))

    return issue_dict, pairs_set

# ---------------------------------------------------------------------------
# 5. Montagem do Objeto DATA no formato exato do Dashboard
# ---------------------------------------------------------------------------
def build_data_payload(issue_dict, pairs_set):
    prj_list = []
    q_list = ["SNOC", "(Sem Fila Equipe)"]
    t_list = []
    st_list = []
    type_ids = {}

    rows = []
    key_to_row_idx = {}

    # Ordena as chaves de forma estável
    sorted_keys = sorted(issue_dict.keys(), reverse=True)

    for k in sorted_keys:
        it = issue_dict[k]
        f = it.get("fields", {})
        
        # Projeto e Número da chave (ex: TI-677266)
        parts = k.split("-")
        prj = parts[0]
        num = int(parts[1]) if len(parts) > 1 and parts[1].isdigit() else 0

        if prj not in prj_list:
            prj_list.append(prj)
        prj_idx = prj_list.index(prj)

        summary = f.get("summary", "")

        # Tipo de Ticket
        t_obj = f.get("issuetype") or {}
        t_name = t_obj.get("name", "Outros")
        t_id = t_obj.get("id")
        if t_name not in t_list:
            t_list.append(t_name)
        t_idx = t_list.index(t_name)
        if t_id:
            type_ids.setdefault(t_name, []).append(t_id)

        # Fila Equipe (customfield_12014)
        q_name = f.get("customfield_12014") or "(Sem Fila Equipe)"
        if q_name not in q_list:
            q_list.append(q_name)
        q_idx = q_list.index(q_name)

        # Status do Ticket
        st_name = (f.get("status") or {}).get("name", "Aberto")
        if st_name not in st_list:
            st_list.append(st_name)
        st_idx = st_list.index(st_name)

        # Motivo e Shift-Left Tier
        m_idx = classify_motive(summary)
        tier_idx = classify_tier(m_idx, q_name)

        # Datas
        c_raw = f.get("created", "")
        c_month = int(c_raw[5:7]) if len(c_raw) >= 7 else 1
        c_int = int(c_raw[:10].replace("-", "")) if len(c_raw) >= 10 else 20260101

        r_raw = f.get("resolutiondate")
        if r_raw:
            r_month = int(r_raw[5:7])
            r_int = int(r_raw[:10].replace("-", ""))
            is_done = 1
        else:
            r_month = 13  # Em aberto
            r_int = 0
            is_done = 0

        # Estrutura exata da linha em rows:
        # [prj, num, summary, t_idx, q_idx, st_idx, m_idx, tier_idx, c_month, r_month, c_int, r_int, is_done]
        row = [
            prj_idx, num, summary, t_idx, q_idx, st_idx,
            m_idx, tier_idx, c_month, r_month, c_int, r_int, is_done
        ]
        key_to_row_idx[k] = len(rows)
        rows.append(row)

    # Array linear de pares (row_idx, person_idx)
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
# 6. Injeção no HTML e Publicação
# ---------------------------------------------------------------------------
def generate_html(payload, template_path="template/index_template.html", output_path="public/index.html"):
    if not os.path.exists(template_path):
        print(f"ERRO: Arquivo de template não encontrado em '{template_path}'.", file=sys.stderr)
        sys.exit(1)

    with open(template_path, "r", encoding="utf-8") as f:
        content = f.read()

    data_json = json.dumps(payload, ensure_ascii=False, separators=(',', ':'))
    
    # Substitui a declaração 'const DATA = {...};' no template
    pattern = r"const DATA = \{.*?\};"
    replacement = f"const DATA = {data_json};"
    
    if re.search(pattern, content, flags=re.DOTALL):
        new_content = re.sub(pattern, replacement, content, count=1, flags=re.DOTALL)
    else:
        new_content = content.replace("__DATA_JSON__", f"const DATA = {data_json};")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Sucesso! Painel atualizado em: {output_path}")
    print(f"Resumo: {len(payload['rows'])} chamados únicos | {len(payload['pairs']) // 2} atendimentos computados.")

def main():
    print("Iniciando extração de dados do Jira...")
    issue_dict, pairs_set = fetch_data()
    payload = build_data_payload(issue_dict, pairs_set)
    generate_html(payload)

if __name__ == "__main__":
    main()
