"""
Coleta de posts do Instagram via Business Discovery (Instagram Graph API, rota oficial da Meta).

Pré-requisitos
    - Conta Instagram profissional (Criador ou Empresa) vinculada a uma Página do Facebook
    - App Meta (tipo Business) em modo de desenvolvimento, com o produto Instagram (login do Facebook)
    - Token de usuário de longa duração com instagram_basic, instagram_manage_insights,
      pages_show_list, pages_read_engagement e business_management
      (sem instagram_manage_insights o Business Discovery devolve o erro #10)
    - Variáveis de ambiente IG_USER_ID (id da SUA conta profissional) e IG_TOKEN

Entrada
    data/perfis/perfis.csv com colunas username,origem,segmento

Saída
    data/raw/instagram/*.json       respostas brutas (cache, permite reexecutar sem gastar cota)
    data/processed/posts.parquet    um post por linha, com taxa de engajamento normalizada
    data/processed/perfis.parquet   um perfil por linha, com faixa de tamanho
    outputs/coleta/coleta_log.json  data da coleta, versão da API, volumes e falhas

Uso
    python -m backend.ingestion.coleta_instagram --perfis data/perfis/perfis.csv --max-posts 150
"""
import argparse
import json
import os
import time
from datetime import datetime, timedelta, timezone

import pandas as pd
import requests
from dotenv import load_dotenv

from backend.config import OUT_COLETA, PERFIS, PROCESSED, RAW_INSTAGRAM

load_dotenv()  # lê IG_USER_ID, IG_TOKEN etc. do arquivo .env na pasta do projeto

API_VERSION = os.getenv("IG_API_VERSION", "v25.0")
BASE_URL = f"https://graph.facebook.com/{API_VERSION}"

PROFILE_FIELDS = "username,name,biography,followers_count,media_count"
MEDIA_FIELDS_FULL = (
    "id,caption,media_type,media_product_type,timestamp,permalink,"
    "like_count,comments_count,view_count,media_url,thumbnail_url"
)
MEDIA_FIELDS_MIN = (
    "id,caption,media_type,media_product_type,timestamp,permalink,"
    "like_count,comments_count,media_url"
)
RATE_LIMIT_CODES = {4, 17, 32, 613}
MIN_AGE_DAYS = 14          # métricas estabilizadas (TAPI, seção 5)
LOOKBACK_DAYS = 365        # padrão; ajustável com --janela-dias

RAW = RAW_INSTAGRAM


class FieldError(Exception):
    pass


class ProfileError(Exception):
    pass


class RateLimitError(Exception):
    pass


class CacheMiss(Exception):
    pass


def _request(username, media_fields, after, limit, ig_user_id, token):
    media = f"media.limit({limit})" + (f".after({after})" if after else "")
    fields = f"business_discovery.username({username}){{{PROFILE_FIELDS},{media}{{{media_fields}}}}}"
    for attempt in range(4):
        r = requests.get(
            f"{BASE_URL}/{ig_user_id}",
            params={"fields": fields, "access_token": token},
            timeout=60,
        )
        if r.ok:
            return r.json()["business_discovery"]
        err = r.json().get("error", {})
        code = err.get("code")
        if r.status_code == 429 or code in RATE_LIMIT_CODES:
            wait = [60, 180, 300, 600][attempt]
            print(f"  limite atingido ({code}), aguardando {wait}s")
            time.sleep(wait)
            continue
        if code == 100 and "field" in err.get("message", "").lower():
            raise FieldError(err.get("message"))
        raise ProfileError(f"{code} {err.get('message')}")
    raise RateLimitError("limite de requisições persistente")


SOMENTE_CACHE = False


def fetch_page(username, page, after, media_fields, ig_user_id, token, limit=50):
    cache = RAW / f"{username}_p{page:03d}.json"
    if cache.exists():
        return json.loads(cache.read_text(encoding="utf-8"))
    if SOMENTE_CACHE:
        raise CacheMiss()
    data = _request(username, media_fields, after, limit, ig_user_id, token)
    cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    time.sleep(1.5)
    return data


def collect_profile(username, max_posts, ig_user_id, token, now, janela_dias=LOOKBACK_DAYS):
    media_fields = MEDIA_FIELDS_FULL
    profile, posts, after, page = None, [], None, 0
    cutoff = now - timedelta(days=janela_dias)
    while len(posts) < max_posts:
        try:
            data = fetch_page(username, page, after, media_fields, ig_user_id, token)
        except CacheMiss:
            break
        except FieldError:
            if media_fields == MEDIA_FIELDS_MIN:
                raise
            print("  campo indisponível, repetindo com campos mínimos")
            media_fields = MEDIA_FIELDS_MIN
            continue
        if profile is None:
            profile = {k: data.get(k) for k in PROFILE_FIELDS.split(",")}
        media = data.get("media", {})
        batch = media.get("data", [])
        posts.extend(batch)
        oldest = min((m["timestamp"] for m in batch), default=None)
        # o Business Discovery devolve só o cursor "after", sem o link "next";
        # a coleta continua enquanto houver cursor e a página vier com posts
        after = media.get("paging", {}).get("cursors", {}).get("after")
        if not batch or not after or (oldest and pd.Timestamp(oldest) < cutoff):
            break
        page += 1
    return profile, posts[:max_posts]


def faixa(followers):
    if followers is None:
        return None
    if followers < 10_000:
        return "micro"
    if followers <= 100_000:
        return "medio"
    return "grande"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--perfis", default=str(PERFIS / "perfis.csv"))
    ap.add_argument("--max-posts", type=int, default=150)
    ap.add_argument("--janela-dias", type=int, default=LOOKBACK_DAYS)
    ap.add_argument("--somente-cache", action="store_true",
                    help="monta as saídas só com as páginas já baixadas, sem chamar a API")
    args = ap.parse_args()
    global SOMENTE_CACHE
    SOMENTE_CACHE = args.somente_cache

    ig_user_id = os.environ["IG_USER_ID"]
    token = os.environ["IG_TOKEN"]
    RAW.mkdir(parents=True, exist_ok=True)

    now = datetime.now(timezone.utc)
    perfis_in = pd.read_csv(args.perfis)
    perfis_out, rows, falhas = [], [], []
    interrompido = None

    for _, p in perfis_in.iterrows():
        user = p["username"].strip().lstrip("@")
        print(f"@{user}")
        try:
            profile, posts = collect_profile(user, args.max_posts, ig_user_id, token, now, args.janela_dias)
        except ProfileError as e:
            print(f"  falha {e}")
            falhas.append({"username": user, "erro": str(e)})
            continue
        except RateLimitError:
            # a partir daqui, segue só com o cache (o que já foi baixado não se perde)
            SOMENTE_CACHE = True
            interrompido = interrompido or user
            print(f"  limite da API persistente; seguindo só com o cache a partir de @{user}")
            profile, posts = collect_profile(user, args.max_posts, ig_user_id, token, now, args.janela_dias)
        if profile is None:
            falhas.append({"username": user, "erro": "sem páginas no cache"})
            continue
        followers = profile.get("followers_count")
        perfis_out.append({
            **profile,
            "origem": p.get("origem"),
            "segmento": p.get("segmento"),
            "faixa": faixa(followers),
            "coletado_em": now.isoformat(),
        })
        for m in posts:
            rows.append({
                "username": user,
                "followers": followers,
                "origem": p.get("origem"),
                "segmento": p.get("segmento"),
                "faixa": faixa(followers),
                **{k: m.get(k) for k in MEDIA_FIELDS_FULL.split(",")},
                "coletado_em": now.isoformat(),
            })

    posts = pd.DataFrame(rows)
    posts["timestamp"] = pd.to_datetime(posts["timestamp"], utc=True)
    posts["idade_dias"] = (now - posts["timestamp"]).dt.days
    posts["likes_ocultos"] = posts["like_count"].isna()
    posts["engajamento"] = (
        posts["like_count"].fillna(0) + posts["comments_count"].fillna(0)
    ) / posts["followers"]
    posts.loc[posts["likes_ocultos"], "engajamento"] = float("nan")

    total_bruto = len(posts)
    posts = posts[(posts["idade_dias"] >= MIN_AGE_DAYS) & (posts["idade_dias"] <= args.janela_dias)]

    posts.to_parquet(PROCESSED / "posts.parquet", index=False)
    pd.DataFrame(perfis_out).to_parquet(PROCESSED / "perfis.parquet", index=False)
    (OUT_COLETA / "coleta_log.json").write_text(json.dumps({
        "coletado_em": now.isoformat(),
        "api": f"Instagram Graph API {API_VERSION}, Business Discovery",
        "perfis_solicitados": len(perfis_in),
        "perfis_coletados": len(perfis_out),
        "posts_brutos": total_bruto,
        "posts_validos": len(posts),
        "posts_likes_ocultos": int(posts["likes_ocultos"].sum()),
        "criterios": {"idade_minima_dias": MIN_AGE_DAYS, "janela_dias": args.janela_dias,
                      "max_posts_por_perfil": args.max_posts},
        "falhas": falhas,
        "somente_cache": args.somente_cache,
        "interrompido_em": interrompido,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{len(perfis_out)} perfis, {len(posts)} posts válidos, {len(falhas)} falhas")
    if interrompido:
        print(f"coleta parcial: limite da API a partir de @{interrompido}. Rode o mesmo comando mais tarde para completar.")


if __name__ == "__main__":
    main()
