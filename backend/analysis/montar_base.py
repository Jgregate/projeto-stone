"""
Monta a base unificada (Instagram + YouTube Shorts), calcula o ranking normalizado,
marca o top 10% e baixa as mídias das publicações de alto desempenho.

Métrica (TAPI 6.1)
    engajamento = (curtidas + comentários) / seguidores (ou inscritos)

Critério de alto desempenho (declarado no README)
    critério "perfil" (padrão)
        lift = engajamento do post / mediana do engajamento do próprio perfil
        alto desempenho = top 10% de lift em cada plataforma, só para perfis com
        pelo menos 10 posts válidos (mediana confiável).
        O lift remove o efeito do tamanho da conta e da audiência de cada perfil e isola
        o efeito do conteúdo. Evita que um único perfil com audiência muito engajada
        domine o top 10%.
    critério "estrato" (comparação)
        top 10% de engajamento dentro de cada combinação plataforma x faixa de tamanho.
    As duas marcações ficam salvas na base (alto_perfil e alto_estrato).

Indicador indireto de lead (TAPI 6.1)
    presença e tipo de chamada para ação na legenda/descrição, por expressões regulares.

Entrada
    data/processed/posts.parquet (coleta_instagram.py) e, se existir, data/processed/youtube_posts.parquet

Saída
    data/processed/base.parquet e base.csv   base completa com ranking
    data/processed/top10.csv                 só as publicações de alto desempenho
    data/raw/midia/<post_id>.jpg             imagem ou frame de cada post do top 10%
    outputs/analise/relatorio_base.md        números da base para a documentação

Uso
    python -m backend.analysis.montar_base
    python -m backend.analysis.montar_base --sem-midia      (pula o download das imagens)
"""
import argparse

import pandas as pd
import requests

from backend.config import MIDIA, OUT_ANALISE, PROCESSED

DATA = PROCESSED
TOP_PCT = 0.90
MIN_GRUPO = 30
MIN_POSTS_PERFIL = 10

CTA_PADROES = {
    "link_na_bio": r"link na bio|link da bio|link no perfil",
    "comentar": r"\bcomenta|\bcomente|deixa nos coment|escreve nos coment",
    "salvar": r"\bsalva\b|\bsalve\b|salva esse|salve esse|salva pra|salve para",
    "dm": r"\bdm\b|direct|me chama|chama no|manda mensagem|whatsapp",
    "seguir": r"\bsegue\b|\bsiga\b|me segue|siga o perfil",
    "compartilhar": r"compartilha|manda pra|envia pra|marca (?:um|uma|alguém|quem)",
}


def tipo_instagram(row):
    if row.get("media_product_type") == "REELS":
        return "reels"
    return {"CAROUSEL_ALBUM": "carrossel", "IMAGE": "imagem", "VIDEO": "video"}.get(row.get("media_type"), "outro")


def carregar_instagram():
    ig = pd.read_parquet(DATA / "posts.parquet")
    return pd.DataFrame({
        "plataforma": "instagram",
        "perfil": ig["username"],
        "post_id": "ig_" + ig["id"].astype(str),
        "url": ig["permalink"],
        "tipo_post": ig.apply(tipo_instagram, axis=1),
        "publicado_em": pd.to_datetime(ig["timestamp"], utc=True),
        "texto": ig["caption"].fillna(""),
        "curtidas": ig["like_count"],
        "comentarios": ig["comments_count"],
        "views": ig.get("view_count"),
        "seguidores": ig["followers"],
        "faixa": ig["faixa"],
        "origem": ig["origem"],
        "segmento": ig["segmento"],
        "duracao_s": None,
        "media_url": ig.get("media_url"),
        "thumbnail_url": ig.get("thumbnail_url"),
        "coletado_em": ig["coletado_em"],
    })


def carregar_youtube():
    path = DATA / "youtube_posts.parquet"
    if not path.exists():
        return pd.DataFrame()
    yt = pd.read_parquet(path)
    if yt.empty:
        return yt
    return pd.DataFrame({
        "plataforma": "youtube",
        "perfil": yt["handle"],
        "post_id": "yt_" + yt["video_id"].astype(str),
        "url": yt["url"],
        "tipo_post": "short",
        "publicado_em": pd.to_datetime(yt["publicado_em"], utc=True),
        "texto": (yt["titulo"].fillna("") + "\n" + yt["descricao"].fillna("")).str.strip(),
        "curtidas": yt["likes"],
        "comentarios": yt["comentarios"],
        "views": yt["views"],
        "seguidores": yt["inscritos"],
        "faixa": yt["faixa"],
        "origem": yt["origem"],
        "segmento": yt["segmento"],
        "duracao_s": yt["duracao_s"],
        "media_url": None,
        "thumbnail_url": yt["thumbnail_url"],
        "coletado_em": yt["coletado_em"],
    })


def ranquear(df):
    df["metrica_valida"] = df["curtidas"].notna() & df["seguidores"].gt(0)
    df["engajamento"] = (df["curtidas"].fillna(0) + df["comentarios"].fillna(0)) / df["seguidores"]
    df.loc[~df["metrica_valida"], "engajamento"] = float("nan")

    valid = df["metrica_valida"]
    df["pct_global"] = df.loc[valid].groupby("plataforma")["engajamento"].rank(pct=True)
    df["pct_estrato"] = df.loc[valid].groupby(["plataforma", "faixa"])["engajamento"].rank(pct=True)
    df["tam_estrato"] = df.groupby(["plataforma", "faixa"])["post_id"].transform("count")
    df["alto_estrato"] = df["pct_estrato"] >= TOP_PCT
    df["estrato_pequeno"] = df["tam_estrato"] < MIN_GRUPO

    df["n_validos_perfil"] = df.loc[valid].groupby(["plataforma", "perfil"])["post_id"].transform("count")
    df["mediana_perfil"] = df.loc[valid].groupby(["plataforma", "perfil"])["engajamento"].transform("median")
    df["lift"] = df["engajamento"] / df["mediana_perfil"].replace(0, float("nan"))
    elegivel = valid & df["n_validos_perfil"].ge(MIN_POSTS_PERFIL) & df["lift"].notna()
    df["pct_lift"] = df.loc[elegivel].groupby("plataforma")["lift"].rank(pct=True)
    df["alto_perfil"] = df["pct_lift"] >= TOP_PCT
    return df


def marcar_cta(df):
    texto = df["texto"].str.lower()
    for nome, padrao in CTA_PADROES.items():
        df[f"cta_{nome}"] = texto.str.contains(padrao, regex=True)
    cols = [f"cta_{n}" for n in CTA_PADROES]
    df["tem_cta"] = df[cols].any(axis=1)
    df["tipos_cta"] = df[cols].apply(lambda r: "|".join(c[4:] for c in cols if r[c]), axis=1)
    return df


def baixar(url, destino):
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    destino.write_bytes(r.content)


def frame_de_video(url, destino):
    import cv2  # opencv-python
    tmp = destino.with_suffix(".mp4")
    baixar(url, tmp)
    cap = cv2.VideoCapture(str(tmp))
    cap.set(cv2.CAP_PROP_POS_MSEC, 1000)
    ok, frame = cap.read()
    cap.release()
    tmp.unlink(missing_ok=True)
    if not ok:
        raise RuntimeError("não foi possível extrair frame")
    cv2.imwrite(str(destino), frame)


def baixar_midias(top):
    MIDIA.mkdir(parents=True, exist_ok=True)
    status = []
    for _, r in top.iterrows():
        destino = MIDIA / f"{r['post_id']}.jpg"
        if destino.exists():
            status.append("ok")
            continue
        try:
            if r["plataforma"] == "youtube" or pd.notna(r["thumbnail_url"]):
                baixar(r["thumbnail_url"], destino)
            elif r["tipo_post"] in ("imagem", "carrossel"):
                baixar(r["media_url"], destino)
            else:
                frame_de_video(r["media_url"], destino)
            status.append("ok")
        except Exception as e:  # noqa: BLE001
            status.append(f"falha: {str(e)[:80]}")
    return status


def relatorio(df, top, criterio):
    linhas = ["# Relatório da base", ""]
    linhas.append(f"- Publicações na base: {len(df)}")
    linhas.append(f"- Publicações com métrica válida: {int(df['metrica_valida'].sum())}")
    nome = "top 10% de lift (post vs mediana do próprio perfil)" if criterio == "perfil" else "top 10% por plataforma e faixa"
    linhas.append(f"- Critério de alto desempenho: {nome}")
    linhas.append(f"- Publicações de alto desempenho: {len(top)}")
    linhas.append(f"- Maior participação de um único perfil no top: {top['perfil'].value_counts(normalize=True).max():.1%}")
    linhas.append(f"- Período: {df['publicado_em'].min():%d/%m/%Y} a {df['publicado_em'].max():%d/%m/%Y}")
    linhas.append(f"- Perfis/canais: {df['perfil'].nunique()}")
    linhas.append("")

    def tabela(titulo, serie):
        linhas.extend([f"## {titulo}", "", serie.to_markdown(), ""])

    tabela("Volume por plataforma e faixa", df.groupby(["plataforma", "faixa"]).size().rename("posts"))
    tabela("Volume por tipo de post", df["tipo_post"].value_counts().rename("posts"))
    tabela("Engajamento mediano por plataforma e faixa",
           df.groupby(["plataforma", "faixa"])["engajamento"].median().round(4).rename("mediana"))
    def comparar(col):
        base = df.loc[df["metrica_valida"], col].value_counts(normalize=True)
        t = top[col].value_counts(normalize=True)
        out = pd.DataFrame({"% base": base, "% top": t}).fillna(0)
        out["razao top/base"] = (out["% top"] / out["% base"]).round(2)
        out[["% base", "% top"]] = (out[["% base", "% top"]] * 100).round(1)
        return out.sort_values("razao top/base", ascending=False)

    tabela("Tipo de post (base vs top)", comparar("tipo_post"))
    tabela("Segmento (base vs top)", comparar("segmento"))
    tabela("Faixa (base vs top)", comparar("faixa"))
    tabela("Top 10% por origem", top["origem"].value_counts().rename("posts"))
    tabela("Perfis mais presentes no top 10%", top["perfil"].value_counts().head(15).rename("posts"))
    tabela("Presença de CTA (base vs top 10%)",
           pd.Series({"base": df["tem_cta"].mean(), "top 10%": top["tem_cta"].mean()}).round(3).rename("proporcao"))

    pequenos = df.loc[df["estrato_pequeno"], ["plataforma", "faixa"]].drop_duplicates()
    if not pequenos.empty:
        linhas.append("## Atenção")
        linhas.append("")
        linhas.append(f"Estratos com menos de {MIN_GRUPO} posts (percentil menos confiável):")
        for _, p in pequenos.iterrows():
            linhas.append(f"- {p['plataforma']} / {p['faixa']}")
        linhas.append("")

    (OUT_ANALISE / "relatorio_base.md").write_text("\n".join(linhas), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sem-midia", action="store_true")
    ap.add_argument("--criterio", choices=["perfil", "estrato"], default="perfil")
    args = ap.parse_args()

    df = pd.concat([carregar_instagram(), carregar_youtube()], ignore_index=True)
    df = df.drop_duplicates("post_id")
    df = marcar_cta(ranquear(df))
    df["alto_desempenho"] = df["alto_perfil"] if args.criterio == "perfil" else df["alto_estrato"]
    top = df[df["alto_desempenho"]].sort_values(["plataforma", "faixa", "engajamento"], ascending=[True, True, False])

    if not args.sem_midia:
        print(f"baixando mídias de {len(top)} publicações do top 10%")
        df.loc[top.index, "midia_status"] = baixar_midias(top)
        top = df.loc[top.index]
        print(f"  {int((top['midia_status'] == 'ok').sum())} ok, {int((top['midia_status'] != 'ok').sum())} falhas")

    df.to_parquet(DATA / "base.parquet", index=False)
    df.to_csv(DATA / "base.csv", index=False, encoding="utf-8")
    top.to_csv(DATA / "top10.csv", index=False, encoding="utf-8")
    relatorio(df, top, args.criterio)

    print(f"\nbase {len(df)} posts, top 10% {len(top)} posts")
    print(df.groupby(["plataforma", "faixa"]).agg(posts=("post_id", "count"),
                                                   top=("alto_desempenho", "sum")).to_string())
    print("\nrelatório em outputs/analise/relatorio_base.md")


if __name__ == "__main__":
    main()
