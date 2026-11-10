"""
Coleta de YouTube Shorts via YouTube Data API v3 (rota oficial e gratuita).

Para cada canal, busca o canal pelo @handle, lê a playlist de uploads (1 unidade de cota por página,
como recomenda o TAPI, em vez do endpoint de busca, que custa 100) e as estatísticas dos vídeos.

Shorts são identificados por duração de até 180 s. A API não tem um campo oficial de Short,
então o critério fica declarado no README.

Entrada
    canais_youtube.csv com colunas handle,origem,segmento

Saída
    data/raw_youtube/*.json        respostas brutas (cache)
    data/youtube_posts.parquet     um vídeo curto por linha
    data/youtube_canais.parquet    um canal por linha
    data/coleta_youtube_log.json   data, critérios, volumes e falhas

Uso
    python coleta_youtube.py --canais canais_youtube.csv --max-videos 150
"""
import argparse
import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

load_dotenv()

MAX_SHORT_S = 180
MIN_AGE_DAYS = 14
LOOKBACK_DAYS = 365

DATA = Path("data")
RAW = DATA / "raw_youtube"


def duracao_s(iso):
    m = re.fullmatch(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return None
    d, h, mi, s = (int(x) if x else 0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def faixa(n):
    if n is None or pd.isna(n):
        return None
    if n < 10_000:
        return "micro"
    if n <= 100_000:
        return "medio"
    return "grande"


def cache_json(nome, fn):
    path = RAW / f"{nome}.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    data = fn()
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def coletar_canal(yt, handle, max_videos):
    canal = cache_json(
        f"{handle}_canal",
        lambda: yt.channels().list(part="snippet,statistics,contentDetails", forHandle=handle).execute(),
    )
    if not canal.get("items"):
        raise LookupError("canal não encontrado pelo handle")
    c = canal["items"][0]
    uploads = c["contentDetails"]["relatedPlaylists"]["uploads"]

    ids, token, page = [], None, 0
    while len(ids) < max_videos:
        resp = cache_json(
            f"{handle}_uploads_p{page:03d}",
            lambda: yt.playlistItems().list(
                part="contentDetails", playlistId=uploads, maxResults=50, pageToken=token
            ).execute(),
        )
        ids += [i["contentDetails"]["videoId"] for i in resp.get("items", [])]
        token = resp.get("nextPageToken")
        page += 1
        if not token:
            break
    ids = ids[:max_videos]

    videos = []
    for k in range(0, len(ids), 50):
        lote = ids[k:k + 50]
        resp = cache_json(
            f"{handle}_videos_{k:04d}",
            lambda: yt.videos().list(part="snippet,statistics,contentDetails", id=",".join(lote)).execute(),
        )
        videos += resp.get("items", [])
    return c, videos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--canais", default="canais_youtube.csv")
    ap.add_argument("--max-videos", type=int, default=150)
    args = ap.parse_args()

    RAW.mkdir(parents=True, exist_ok=True)
    yt = build("youtube", "v3", developerKey=os.environ["YOUTUBE_API_KEY"], cache_discovery=False)
    now = datetime.now(timezone.utc)

    canais_in = pd.read_csv(args.canais)
    canais_out, rows, falhas = [], [], []

    for _, ch in canais_in.iterrows():
        handle = ch["handle"].strip().lstrip("@")
        print(f"@{handle}")
        try:
            c, videos = coletar_canal(yt, handle, args.max_videos)
        except (LookupError, HttpError) as e:
            print(f"  falha {e}")
            falhas.append({"handle": handle, "erro": str(e)[:200]})
            continue

        st = c.get("statistics", {})
        subs = None if st.get("hiddenSubscriberCount") else int(st.get("subscriberCount", 0))
        canais_out.append({
            "handle": handle,
            "canal_id": c["id"],
            "nome": c["snippet"]["title"],
            "inscritos": subs,
            "origem": ch.get("origem"),
            "segmento": ch.get("segmento"),
            "faixa": faixa(subs),
            "coletado_em": now.isoformat(),
        })
        for v in videos:
            vs, sn = v.get("statistics", {}), v["snippet"]
            dur = duracao_s(v["contentDetails"].get("duration"))
            thumbs = sn.get("thumbnails", {})
            thumb = (thumbs.get("maxres") or thumbs.get("high") or thumbs.get("medium") or {}).get("url")
            rows.append({
                "handle": handle,
                "inscritos": subs,
                "origem": ch.get("origem"),
                "segmento": ch.get("segmento"),
                "faixa": faixa(subs),
                "video_id": v["id"],
                "titulo": sn.get("title"),
                "descricao": sn.get("description"),
                "tags": "|".join(sn.get("tags", [])),
                "publicado_em": sn.get("publishedAt"),
                "duracao_s": dur,
                "views": int(vs["viewCount"]) if "viewCount" in vs else None,
                "likes": int(vs["likeCount"]) if "likeCount" in vs else None,
                "comentarios": int(vs["commentCount"]) if "commentCount" in vs else None,
                "thumbnail_url": thumb,
                "url": f"https://www.youtube.com/shorts/{v['id']}",
                "coletado_em": now.isoformat(),
            })

    df = pd.DataFrame(rows)
    total_bruto = len(df)
    if not df.empty:
        df["publicado_em"] = pd.to_datetime(df["publicado_em"], utc=True)
        df["idade_dias"] = (now - df["publicado_em"]).dt.days
        df = df[
            (df["duracao_s"] <= MAX_SHORT_S)
            & (df["idade_dias"] >= MIN_AGE_DAYS)
            & (df["idade_dias"] <= LOOKBACK_DAYS)
        ]

    df.to_parquet(DATA / "youtube_posts.parquet", index=False)
    pd.DataFrame(canais_out).to_parquet(DATA / "youtube_canais.parquet", index=False)
    (DATA / "coleta_youtube_log.json").write_text(json.dumps({
        "coletado_em": now.isoformat(),
        "api": "YouTube Data API v3 (channels.list forHandle, playlistItems.list, videos.list)",
        "canais_solicitados": len(canais_in),
        "canais_coletados": len(canais_out),
        "videos_brutos": total_bruto,
        "shorts_validos": len(df),
        "criterios": {"duracao_max_s": MAX_SHORT_S, "idade_minima_dias": MIN_AGE_DAYS,
                      "janela_dias": LOOKBACK_DAYS, "max_videos_por_canal": args.max_videos},
        "falhas": falhas,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"\n{len(canais_out)} canais, {len(df)} shorts válidos, {len(falhas)} falhas")


if __name__ == "__main__":
    main()
