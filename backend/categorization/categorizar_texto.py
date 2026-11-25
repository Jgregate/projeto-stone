"""
Categorização híbrida do top 10% (corrige o colapso do VLM local de 2B).

Por que existe
    O qwen3-vl:2b local respondeu quase sempre a mesma coisa (100% talking_head,
    100% empreendedor real, 97% com CTA, notas médias 9,9). Por isso cada campo
    da rubrica passa a vir da fonte mais confiável para ele.

Fonte de cada campo
    legenda  -> Groq qwen/qwen3.8-27b, só texto, em lotes de 10 posts
                formato_video (provável), gancho, tipo_hook, forca_hook, tema, empreendedor real,
                prova social, tom, linguagem regional, clareza, CTA, tipo de CTA, oferta, elementos_top5
    imagem   -> detector de rostos do OpenCV (tem_rosto), determinístico
    imagem   -> VLM local (texto_na_tela), único campo visual com distribuição plausível

Entrada
    data/processed/base.parquet, data/raw/midia/, data/processed/categorias.parquet (rodada do VLM local)

Saída
    data/processed/categorias_vlm.parquet   cópia da rodada só com o VLM (comparação)
    data/processed/categorias_texto.jsonl   cache das respostas do Groq
    data/processed/categorias.parquet       versão híbrida, usada por validacao.py e analisar_top.py

Uso
    python -m backend.categorization.categorizar_texto --limite 20     (teste)
    python -m backend.categorization.categorizar_texto
"""
import argparse
import json
import os
import shutil
import time
from datetime import datetime, timezone

import cv2
import pandas as pd
import requests
from dotenv import load_dotenv
from pydantic import ValidationError

from backend.config import MIDIA, MODELOS, PROCESSED
from backend.prompts.categorizacao_texto import PROMPT
from backend.schemas.rubrica import Lote

load_dotenv()

URL = "https://api.groq.com/openai/v1/chat/completions"
MODELO = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")
DATA = PROCESSED
CACHE = DATA / "categorias_texto.jsonl"
LOTE = 10
MAX_CHARS = 500


def chamar(mensagens, chave):
    payload = {"model": MODELO, "messages": mensagens, "temperature": 0,
               "response_format": {"type": "json_object"}, "max_completion_tokens": 2500,
               "reasoning_effort": "none"}
    for tentativa in range(10):
        r = requests.post(URL, headers={"Authorization": f"Bearer {chave}"}, json=payload, timeout=180)
        if r.status_code == 429:
            espera = float(r.headers.get("retry-after", 20 * (tentativa + 1)))
            if espera > 600:
                raise RuntimeError(f"limite diário do Groq atingido (retry-after {espera:.0f}s)")
            print(f"    429, aguardando {espera:.0f}s")
            time.sleep(espera + 1)
            continue
        if r.status_code == 400 and "reasoning" in r.text and "reasoning_effort" in payload:
            payload.pop("reasoning_effort")
            continue
        if r.status_code >= 500:
            time.sleep(10 * (tentativa + 1))
            continue
        if r.status_code >= 400:
            raise RuntimeError(f"Groq {r.status_code} {r.text[:300]}")
        return r.json()["choices"][0]["message"]["content"]
    raise RuntimeError("limite do Groq persistente")


def categorizar_lote(posts, chave):
    itens = [{"id": p["post_id"], "plataforma": p["plataforma"], "tipo_post": p["tipo_post"],
              "perfil": p["perfil"], "texto": (p["texto"] or "")[:MAX_CHARS]} for p in posts]
    msgs = [{"role": "system", "content": PROMPT},
            {"role": "user", "content": json.dumps(itens, ensure_ascii=False)}]
    resp = chamar(msgs, chave)
    try:
        lote = Lote.model_validate_json(resp)
    except ValidationError as e:
        msgs += [{"role": "assistant", "content": resp},
                 {"role": "user", "content": f"O JSON não seguiu o formato. Erros: {e.errors()[:5]}. "
                                             "Responda de novo só com o JSON corrigido."}]
        lote = Lote.model_validate_json(chamar(msgs, chave))
    ids = {p["post_id"] for p in posts}
    return [r for r in lote.resultados if r.id in ids]


CASCADE = MODELOS / "haarcascade_frontalface_default.xml"
_FACE = None


def detector():
    """Carrega o detector Haar uma vez. No OpenCV 5 ele fica no pacote de extras."""
    global _FACE
    if _FACE is None:
        Classe = getattr(cv2, "CascadeClassifier", None) or getattr(getattr(cv2, "xobjdetect", None), "CascadeClassifier", None)
        if Classe is None:
            raise SystemExit(
                "o OpenCV instalado não tem o detector de rostos (OpenCV 5 sem extras).\n"
                "rode  pip install \"opencv-python<5\"  e tente de novo")
        _FACE = Classe(str(CASCADE))
        if _FACE.empty():
            raise SystemExit(f"detector de rostos não encontrado em {CASCADE}")
    return _FACE


def tem_rosto(post_id):
    path = MIDIA / f"{post_id}.jpg"
    if not path.exists():
        return None
    img = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if img is None:
        return None
    h, w = img.shape
    escala = 640 / max(h, w)
    if escala < 1:
        img = cv2.resize(img, (int(w * escala), int(h * escala)))
    faces = detector().detectMultiScale(img, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
    return len(faces) > 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limite", type=int, default=None)
    args = ap.parse_args()
    chave = os.environ["GROQ_API_KEY"]

    vlm_path = DATA / "categorias_vlm.parquet"
    if not vlm_path.exists():
        shutil.copy(DATA / "categorias.parquet", vlm_path)
        print("rodada do VLM local copiada para data/processed/categorias_vlm.parquet")
    vlm = pd.read_parquet(vlm_path)

    base = pd.read_parquet(DATA / "base.parquet")
    top = base[base["alto_desempenho"]].copy()

    feitos = {}
    if CACHE.exists():
        for linha in CACHE.read_text(encoding="utf-8").splitlines():
            reg = json.loads(linha)
            if reg.get("modelo") == MODELO:
                feitos[reg["post_id"]] = reg
    pend = top[~top["post_id"].isin(feitos)]
    if args.limite:
        pend = pend.head(args.limite)
    print(f"modelo {MODELO} | top 10%: {len(top)} | já feitos: {len(feitos)} | nesta execução: {len(pend)}")

    registros = pend.to_dict("records")
    with CACHE.open("a", encoding="utf-8") as f:
        for i in range(0, len(registros), LOTE):
            lote = registros[i:i + LOTE]
            ini = time.time()
            try:
                res = categorizar_lote(lote, chave)
            except Exception as e:  # noqa: BLE001
                print(f"  lote {i // LOTE + 1} falhou: {str(e)[:150]}")
                if "limite diário" in str(e):
                    break
                continue
            for r in res:
                f.write(json.dumps({"post_id": r.id, "modelo": MODELO,
                                    "executado_em": datetime.now(timezone.utc).isoformat(),
                                    "rubrica": r.model_dump(exclude={"id"})}, ensure_ascii=False) + "\n")
                feitos[r.id] = {"rubrica": r.model_dump(exclude={"id"})}
            f.flush()
            print(f"  lote {i // LOTE + 1}: {len(res)}/{len(lote)} ok ({time.time() - ini:.0f}s) | total {len(feitos)}/{len(top)}")

    # monta a versão híbrida
    txt = pd.DataFrame([{"post_id": k, **v["rubrica"]} for k, v in feitos.items()])
    if txt.empty:
        print("nenhuma categorização de texto ainda")
        return
    txt["elementos_top5"] = txt["elementos_top5"].apply(lambda x: "|".join(x))

    from backend.categorization.categorizar import duracao_faixa, legenda_tamanho
    hib = top.rename(columns={"tem_cta": "cta_regex", "tipos_cta": "tipos_cta_regex"})
    hib = hib.merge(txt, on="post_id", how="inner")
    hib = hib.merge(vlm[["post_id", "texto_na_tela"]], on="post_id", how="left")
    hib["ritmo_cortes_0a10"] = None
    hib["legenda_tamanho"] = hib["texto"].apply(legenda_tamanho)
    hib["duracao_faixa"] = hib["duracao_s"].apply(duracao_faixa)
    print("detectando rostos com OpenCV...")
    hib["tem_rosto"] = hib["post_id"].apply(tem_rosto)
    hib["modelo"] = f"hibrido: texto {MODELO} | rosto opencv | texto_na_tela vlm local"
    hib.to_parquet(DATA / "categorias.parquet", index=False)

    print(f"\nversão híbrida com {len(hib)} de {len(top)} posts -> data/processed/categorias.parquet")
    for c in ["formato_video", "tem_rosto", "criador_e_empreendedor_real", "tem_cta", "tipo_cta", "prova_social"]:
        print(f"  {c:<28} {hib[c].astype(str).value_counts(normalize=True).round(2).to_dict()}")
    print(f"  forca_hook média {hib['forca_hook_0a10'].mean():.1f} | clareza média {hib['clareza_mensagem_0a10'].mean():.1f}")


if __name__ == "__main__":
    main()
