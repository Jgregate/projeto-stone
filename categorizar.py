"""
Categoriza as publicações de alto desempenho com um modelo de visão e linguagem (VLM) no Groq,
aplicando a rubrica fixa do TAPI (rubrica.py). Nível 1 = legenda + imagem de capa.

Cada resposta é validada com Pydantic. Respostas inválidas são reenviadas uma vez com o erro.
Resultados vão para um cache JSONL, então a execução pode ser interrompida e retomada.
Erros 429 respeitam o cabeçalho retry-after do Groq.

Entrada
    data/base.parquet e data/midia/<post_id>.jpg (montar_base.py)

Saída
    data/categorias.jsonl     uma linha por post (cache e registro das execuções)
    data/categorias.parquet   top 10% + rubrica + campos determinísticos

Uso
    python categorizar.py --limite 5        (teste rápido)
    python categorizar.py                   (todos os posts do top 10%)
"""
import argparse
import base64
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import pandas as pd
import requests
from dotenv import load_dotenv
from pydantic import ValidationError

from rubrica import PROMPT_SISTEMA, Rubrica

load_dotenv()

URL = "https://api.groq.com/openai/v1/chat/completions"
MODELO_PADRAO = os.getenv("GROQ_MODEL", "qwen/qwen3.6-27b")
DATA = Path("data")
CACHE = DATA / "categorias.jsonl"
MAX_LADO = 768


def imagem_base64(path):
    if not Path(path).exists():
        return None
    img = cv2.imread(str(path))
    if img is None:
        return None
    h, w = img.shape[:2]
    escala = MAX_LADO / max(h, w)
    if escala < 1:
        img = cv2.resize(img, (int(w * escala), int(h * escala)))
    ok, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 85])
    return base64.b64encode(buf).decode() if ok else None


def legenda_tamanho(texto):
    n = len(texto or "")
    return "curta" if n < 150 else "media" if n < 600 else "longa"


def duracao_faixa(s):
    if s is None or pd.isna(s):
        return None
    return "ate_15s" if s <= 15 else "15_30s" if s <= 30 else "30_60s" if s <= 60 else "60_180s"


def chamar(modelo, mensagens, chave, usar_reasoning=True):
    payload = {
        "model": modelo,
        "messages": mensagens,
        "temperature": 0,
        "response_format": {"type": "json_object"},
        "max_completion_tokens": 900,
    }
    if usar_reasoning:
        payload["reasoning_effort"] = "none"
    for tentativa in range(8):
        r = requests.post(URL, headers={"Authorization": f"Bearer {chave}"}, json=payload, timeout=120)
        if r.status_code == 429:
            espera = float(r.headers.get("retry-after", 20 * (tentativa + 1)))
            print(f"    429, aguardando {espera:.0f}s")
            time.sleep(espera + 1)
            continue
        if r.status_code >= 500:
            time.sleep(10 * (tentativa + 1))
            continue
        if r.status_code == 400 and usar_reasoning and "reasoning" in r.text:
            return chamar(modelo, mensagens, chave, usar_reasoning=False)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]
    raise RuntimeError("limite do Groq persistente")


def categorizar_post(post, modelo, chave):
    img = imagem_base64(DATA / "midia" / f"{post['post_id']}.jpg")
    texto = (post["texto"] or "")[:1500]
    conteudo = [{"type": "text", "text":
                 f"tipo_post: {post['tipo_post']}\nplataforma: {post['plataforma']}\n\nTEXTO DA PUBLICAÇÃO\n{texto}"}]
    if img:
        conteudo.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img}"}})
    mensagens = [{"role": "system", "content": PROMPT_SISTEMA}, {"role": "user", "content": conteudo}]

    resposta = chamar(modelo, mensagens, chave)
    try:
        return Rubrica.model_validate_json(resposta), bool(img), 1
    except ValidationError as e:
        mensagens += [
            {"role": "assistant", "content": resposta},
            {"role": "user", "content": f"O JSON não seguiu a rubrica. Erros: {e.errors()[:5]}. "
                                        "Responda de novo só com o JSON corrigido."},
        ]
        resposta = chamar(modelo, mensagens, chave)
        return Rubrica.model_validate_json(resposta), bool(img), 2


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limite", type=int, default=None)
    ap.add_argument("--modelo", default=MODELO_PADRAO)
    ap.add_argument("--parte", default=None,
                    help="divide os pendentes, ex. 1/2 e 2/2 em dois terminais (um modelo em cada)")
    args = ap.parse_args()

    chave = os.environ["GROQ_API_KEY"]
    base = pd.read_parquet(DATA / "base.parquet")
    top = base[base["alto_desempenho"]].copy()

    feitos = {}
    if CACHE.exists():
        for linha in CACHE.read_text(encoding="utf-8").splitlines():
            reg = json.loads(linha)
            if reg.get("ok"):
                feitos[reg["post_id"]] = reg

    pendentes = top[~top["post_id"].isin(feitos)]
    if args.parte:
        i, n = (int(x) for x in args.parte.split("/"))
        pendentes = pendentes.iloc[i - 1::n]
    if args.limite:
        pendentes = pendentes.head(args.limite)
    print(f"top 10%: {len(top)} | já categorizados: {len(feitos)} | nesta execução: {len(pendentes)}")

    with CACHE.open("a", encoding="utf-8") as f:
        for i, (_, post) in enumerate(pendentes.iterrows(), 1):
            inicio = time.time()
            reg = {"post_id": post["post_id"], "modelo": args.modelo,
                   "executado_em": datetime.now(timezone.utc).isoformat()}
            try:
                rub, com_imagem, tentativas = categorizar_post(post, args.modelo, chave)
                reg.update(ok=True, com_imagem=com_imagem, tentativas=tentativas, rubrica=rub.model_dump())
                print(f"[{i}/{len(pendentes)}] {post['post_id']} ok ({time.time() - inicio:.1f}s)")
            except Exception as e:  # noqa: BLE001
                reg.update(ok=False, erro=str(e)[:300])
                print(f"[{i}/{len(pendentes)}] {post['post_id']} falha {str(e)[:120]}")
            f.write(json.dumps(reg, ensure_ascii=False) + "\n")
            f.flush()

    # consolida tudo o que está no cache
    regs = {}
    for linha in CACHE.read_text(encoding="utf-8").splitlines():
        reg = json.loads(linha)
        if reg.get("ok"):
            regs[reg["post_id"]] = reg
    linhas = [{"post_id": k, "modelo": v["modelo"], "com_imagem": v["com_imagem"], **v["rubrica"]}
              for k, v in regs.items()]
    cat = pd.DataFrame(linhas)
    if cat.empty:
        print("nenhuma categorização válida ainda")
        return
    cat["elementos_top5"] = cat["elementos_top5"].apply(lambda x: "|".join(x))
    # a base já tem tem_cta (detecção por regex do dia 2); renomeia para não colidir com a rubrica
    top = top.rename(columns={"tem_cta": "cta_regex", "tipos_cta": "tipos_cta_regex"})
    out = top.merge(cat, on="post_id", how="inner")
    out["legenda_tamanho"] = out["texto"].apply(legenda_tamanho)
    out["duracao_faixa"] = out["duracao_s"].apply(duracao_faixa)
    out.to_parquet(DATA / "categorias.parquet", index=False)
    print(f"\ncategorizados {len(out)} de {len(top)} posts do top 10% -> data/categorias.parquet")


if __name__ == "__main__":
    main()
