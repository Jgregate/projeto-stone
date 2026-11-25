"""
Valida a lista de candidatos antes da coleta completa.

Para cada @ do data/perfis/candidatos.csv, consulta o Business Discovery (1 chamada por perfil) e registra
se a conta é profissional e acessível, seguidores, número de posts, data do último post,
se está ativa nos últimos 12 meses e a faixa de tamanho.

Entrada
    candidatos.csv com colunas username,origem,segmento,como_encontrei

Saída
    data/perfis/perfis_validados.csv  todos os candidatos com status e métricas
    data/perfis/perfis.csv            só os aprovados, pronto para o coleta_instagram.py

Uso
    python -m backend.ingestion.validar_perfis --entrada data/perfis/candidatos.csv
"""
import argparse
import os
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests
from dotenv import load_dotenv

from backend.config import PERFIS

load_dotenv()

API_VERSION = os.getenv("IG_API_VERSION", "v27.0")
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

# Balanceamento por faixa (evita viés de sobrevivência, TAPI seção 5)
# Contas grandes acima do limite são excluídas seguindo esta prioridade de origem,
# e dentro da mesma origem ficam as de MENOS seguidores (mais próximas da escala do MPE).
PRIORIDADE_ORIGEM = {
    "ecossistema_stone": 1,
    "concorrente_fintech": 2,
    "criador_mpe": 3,
    "plataforma_mpe": 4,
    "curadoria_setor": 5,
}
FIXOS = {"impulsostone", "sebrae", "nathfinancas"}  # sempre mantidos (case e Semana do MEI)
EXCLUIR = {
    "tonpagamentos": "conta não oficial da Ton (poucos seguidores)",
    "ton": "conta não oficial da Ton (poucos seguidores)",
    "sumupbrasil": "conta não oficial da SumUp (poucos seguidores)",
    "c6bank": "banco generalista, sem foco declarado em MPE",
}


def faixa(followers):
    if followers is None:
        return None
    if followers < 10_000:
        return "micro"
    if followers <= 100_000:
        return "medio"
    return "grande"


def checar(username, ig_user_id, token):
    fields = (
        f"business_discovery.username({username})"
        "{username,name,followers_count,media_count,media.limit(5){timestamp}}"
    )
    r = requests.get(
        f"{BASE_URL}/{ig_user_id}",
        params={"fields": fields, "access_token": token},
        timeout=60,
    )
    data = r.json()
    if not r.ok:
        return {"status": "erro", "detalhe": data.get("error", {}).get("message", "")[:120]}
    bd = data["business_discovery"]
    datas = [m["timestamp"] for m in bd.get("media", {}).get("data", [])]
    ultimo = max(datas) if datas else None
    return {
        "status": "ok",
        "nome": bd.get("name"),
        "followers": bd.get("followers_count"),
        "media_count": bd.get("media_count"),
        "ultimo_post": ultimo,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--entrada", default=str(PERFIS / "candidatos.csv"))
    ap.add_argument("--max-grande", type=int, default=15)
    args = ap.parse_args()

    ig_user_id = os.environ["IG_USER_ID"]
    token = os.environ["IG_TOKEN"]
    limite_atividade = datetime.now(timezone.utc) - timedelta(days=365)

    cand = pd.read_csv(args.entrada)
    cand["username"] = cand["username"].str.strip().str.lstrip("@").str.lower()
    cand = cand.drop_duplicates("username")

    linhas = []
    for _, c in cand.iterrows():
        res = checar(c["username"], ig_user_id, token)
        linhas.append({**c.to_dict(), **res})
        print(f"@{c['username']:<30} {res['status']:<5} {res.get('followers') or res.get('detalhe', '')}")
        time.sleep(1.5)

    df = pd.DataFrame(linhas)
    df["faixa"] = df["followers"].apply(lambda f: faixa(f) if pd.notna(f) else None)
    df["ultimo_post"] = pd.to_datetime(df["ultimo_post"], utc=True)
    df["ativo_12m"] = df["ultimo_post"] >= limite_atividade
    df["aprovado"] = (df["status"] == "ok") & df["ativo_12m"]
    df["motivo"] = None
    df.loc[df["status"] != "ok", "motivo"] = "conta inexistente, pessoal ou inacessível"
    df.loc[(df["status"] == "ok") & ~df["ativo_12m"], "motivo"] = "sem posts nos últimos 12 meses"
    for u, motivo in EXCLUIR.items():
        m = df["username"] == u
        df.loc[m, "aprovado"] = False
        df.loc[m, "motivo"] = f"excluído na curadoria manual ({motivo})"

    # balanceamento das contas grandes
    grandes = df[df["aprovado"] & (df["faixa"] == "grande")].copy()
    if len(grandes) > args.max_grande:
        grandes["fixo"] = grandes["username"].isin(FIXOS)
        grandes["prio"] = grandes["origem"].map(PRIORIDADE_ORIGEM).fillna(9)
        grandes = grandes.sort_values(["fixo", "prio", "followers"], ascending=[False, True, True])
        excluir = grandes.index[args.max_grande:]
        df.loc[excluir, "aprovado"] = False
        df.loc[excluir, "motivo"] = "excluído por balanceamento de faixa (excesso de contas grandes)"

    df.to_csv(PERFIS / "perfis_validados.csv", index=False, encoding="utf-8")

    aprovados = df[df["aprovado"]]
    aprovados[["username", "origem", "segmento"]].to_csv(PERFIS / "perfis.csv", index=False, encoding="utf-8")

    print("\nResumo")
    print(f"  candidatos {len(df)}, aprovados {len(aprovados)}")
    print("  aprovados por faixa")
    print(aprovados["faixa"].value_counts().to_string())
    print("  aprovados por origem")
    print(aprovados["origem"].value_counts().to_string())
    print("  excluídos (curadoria manual e balanceamento)")
    for u in df.loc[df["motivo"].str.startswith("excluído", na=False), "username"]:
        print(f"    @{u}")


if __name__ == "__main__":
    main()
