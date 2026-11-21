"""
Frontend de demonstração do agente de conteúdo para MPEs (Stone · Inteli Academy).

Serve uma página web e uma API HTTP fina sobre o agente. A API usa exatamente o contrato
de agente.py (Entrada e Saida) e só acrescenta dados lidos da base, para que a tela mostre
números reais e nunca números escritos pelo modelo.

Rodar (na raiz do repositório)
    .venv\\Scripts\\python.exe frontend\\app.py

Variáveis opcionais
    PORTA_FRONTEND        porta local (padrão 8000)
    ABRIR_NAVEGADOR=0     não abre o navegador ao iniciar
    SIMULAR_LIMITE=1      força o erro 429 do modelo, para testar a tela de limite
"""
import json
import os
import re
import sys
import threading
import time
import webbrowser
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import requests  # noqa: E402
from fastapi import FastAPI  # noqa: E402
from fastapi.responses import FileResponse, JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

import agente  # noqa: E402
from agente import Entrada, _norm, carregar, executar  # noqa: E402

ESTATICO = Path(__file__).resolve().parent / "static"
MIDIA = RAIZ / "data" / "midia"
ACHADOS = RAIZ / "data" / "achados.json"

# --------------------------------------------------------------------------- limite do modelo (429)
# O _llm original espera até 300 s a cada 429 e tenta 6 vezes. Numa demonstração ao vivo isso
# congela a tela. Aqui a chamada espera no máximo uma vez, por poucos segundos, e depois devolve
# o limite para a interface. A lógica de montagem do pedido é a mesma de agente._llm.


class LimiteDoModelo(RuntimeError):
    def __init__(self, espera):
        super().__init__(f"limite de requisições do modelo, tente em {espera:.0f} s")
        self.espera = espera


_trava = threading.Lock()
_ocorrencias = {"limite": None, "falha": None}


def _llm_demo(sistema, usuario, max_tokens=2500):
    if os.getenv("SIMULAR_LIMITE") == "1":
        _ocorrencias["limite"] = 30.0
        raise LimiteDoModelo(30.0)
    chave = os.getenv("GROQ_API_KEY")
    if not chave:
        _ocorrencias["falha"] = "chave do Groq ausente no .env"
        raise RuntimeError("GROQ_API_KEY ausente")
    modelo = agente.MODELO_LLM
    payload = {"model": modelo, "temperature": 0.4, "response_format": {"type": "json_object"},
               "max_completion_tokens": max_tokens,
               "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}]}
    if "gpt-oss" in modelo:
        payload["reasoning_effort"] = "low"
    esperou = False
    for _ in range(4):
        try:
            r = requests.post(agente.URL, headers={"Authorization": f"Bearer {chave}"}, json=payload, timeout=120)
        except requests.RequestException as err:
            _ocorrencias["falha"] = "sem conexão com o Groq"
            raise RuntimeError(str(err)) from err
        if r.status_code == 429:
            espera = float(r.headers.get("retry-after", 20))
            if not esperou and espera <= 8:
                esperou = True
                time.sleep(espera + 0.5)
                continue
            _ocorrencias["limite"] = espera
            raise LimiteDoModelo(espera)
        if r.status_code == 400 and "reasoning" in r.text and "reasoning_effort" in payload:
            payload.pop("reasoning_effort")
            continue
        if r.status_code >= 400:
            _ocorrencias["falha"] = f"o Groq respondeu {r.status_code}"
            raise RuntimeError(f"Groq {r.status_code} {r.text[:200]}")
        conteudo = r.json()["choices"][0]["message"]["content"] or "{}"
        return json.loads(conteudo)
    _ocorrencias["falha"] = "o Groq não respondeu depois de várias tentativas"
    raise RuntimeError("Groq sem resposta")


agente._llm = _llm_demo

# --------------------------------------------------------------------------- dados auxiliares

PALAVRAS_VAZIAS = set("""
para como qual quais mais menos sobre esse essa isso este esta isto aqui pelo pela pelos pelas
entre quando onde porque fazer faz feito preciso quero queria pode podem deve devem tenho temos
cada muito muita muitos muitas outro outra outros outras ainda tambem desde voce voces seus suas
stone publicacao publicacoes post posts conteudo conteudos criativo criativos gerar criar ideia
ideias melhor melhores alto desempenho engajamento instagram youtube shorts reels carrossel
""".split())

RE_POST = re.compile(r"\b(ig_\d{6,}|yt_[A-Za-z0-9_-]{11})")


def _midia_disponivel():
    if not MIDIA.exists():
        return set()
    return {p.stem for p in MIDIA.glob("*.jpg")}


def _num(v, casas=None):
    try:
        if v is None or v != v:  # NaN
            return None
        return round(float(v), casas) if casas is not None else float(v)
    except (TypeError, ValueError):
        return None


def _txt(v):
    return None if v is None or (isinstance(v, float) and v != v) else str(v)


def _detalhe(linha, midia):
    pid = linha["post_id"]
    texto = _txt(linha.get("texto")) or ""
    return {
        "post_id": pid,
        "perfil": linha.get("perfil"),
        "plataforma": linha.get("plataforma"),
        "tipo_post": linha.get("tipo_post"),
        "url": linha.get("url"),
        "publicado_em": str(linha["publicado_em"])[:10] if linha.get("publicado_em") is not None else None,
        "curtidas": _num(linha.get("curtidas")),
        "comentarios": _num(linha.get("comentarios")),
        "seguidores": _num(linha.get("seguidores")),
        "engajamento": _num(linha.get("engajamento"), 5),
        "lift": _num(linha.get("lift"), 2),
        "faixa": _txt(linha.get("faixa")),
        "segmento": _txt(linha.get("segmento")),
        "tema_principal": _txt(linha.get("tema_principal")),
        "tipo_hook": _txt(linha.get("tipo_hook")),
        "formato_video": _txt(linha.get("formato_video")),
        "tom": _txt(linha.get("tom")),
        "tipo_cta": _txt(linha.get("tipo_cta")),
        "texto": texto[:280] + ("…" if len(texto) > 280 else ""),
        "imagem": f"/midia/{pid}.jpg" if pid in midia else None,
    }


def _indice():
    cat, base = carregar()
    return cat.set_index("post_id", drop=False), base.set_index("post_id", drop=False)


# --------------------------------------------------------------------------- API

app = FastAPI(title="Jade", docs_url="/api/docs", redoc_url=None)


def _erro(status, codigo, mensagem, **extra):
    return JSONResponse(status_code=status, content={"erro": codigo, "mensagem": mensagem, **extra})


@app.post("/api/consultar")
def consultar(entrada: Entrada):
    if not entrada.query.strip():
        return _erro(400, "pedido_vazio", "Escreva o pedido antes de consultar.")

    cat, _ = carregar()
    termos = [t for t in _norm(entrada.query).split() if len(t) > 3 and t not in PALAVRAS_VAZIAS]
    if termos:
        casa = cat["_busca"].apply(lambda b: any(t in b for t in termos))
        if not casa.any():
            return _erro(404, "sem_resultado",
                         "Nenhuma publicação de alto desempenho fala desse assunto.", termos=termos)

    with _trava:
        _ocorrencias.update(limite=None, falha=None)
        saida = executar(entrada)
        limite, falha = _ocorrencias["limite"], _ocorrencias["falha"]

    if saida.n_posts_analisados == 0 or not saida.reference_posts:
        return _erro(404, "sem_resultado", "Nenhuma publicação de alto desempenho atende a esses filtros.")

    idx_cat, idx_base = _indice()
    midia = _midia_disponivel()
    detalhes = {}
    for p in saida.reference_posts:
        if p.post_id in idx_cat.index:
            detalhes[p.post_id] = _detalhe(idx_cat.loc[p.post_id].to_dict(), midia)

    textos = [saida.explanation, *saida.recomendacoes]
    for c in saida.creatives:
        textos += [c.justificativa, *c.inspirado_em]
    citados = {}
    for pid in set(RE_POST.findall(" ".join(textos))):
        if pid in idx_base.index:
            linha = idx_base.loc[pid]
            citados[pid] = {"na_base": True, "url": linha["url"], "perfil": linha["perfil"]}
        else:
            citados[pid] = {"na_base": False}

    # exemplos reais de cada achado, no mesmo recorte usado pelo agente
    ap = dict(saida.filtros_aplicados)
    seg = ap.pop("segmento", None)
    sub, _, _ = agente.filtrar(cat, seg, {k: v for k, v in ap.items() if v}, relaxar=False)
    exemplos_achados = {}
    for f in saida.findings:
        if f.campo not in sub.columns:
            continue
        s = sub[sub[f.campo].astype(str) == f.valor].sort_values("lift", ascending=False).head(3)
        exemplos_achados[f"{f.campo}|{f.valor}"] = [
            {"post_id": r.post_id, "perfil": r.perfil, "url": r.url, "lift": _num(r.lift, 2),
             "engajamento": _num(r.engajamento, 5)} for r in s.itertuples()]

    corpo = {
        "saida": saida.model_dump(),
        "exemplos_achados": exemplos_achados,
        "detalhes": detalhes,
        "citados": citados,
        "filtros_pedidos": {"segmento": entrada.segment, **entrada.filters.model_dump()},
        "texto_do_modelo": falha is None and limite is None,
        "falha_modelo": falha,
    }
    if limite is not None:
        return JSONResponse(status_code=429, content={
            "erro": "limite", "retry_after": round(limite),
            "mensagem": "O modelo de linguagem atingiu o limite de requisições.", **corpo})
    return corpo


@app.get("/api/base")
def visao_da_base():
    cat, base = carregar()
    midia = _midia_disponivel()
    validos = base[base["metrica_valida"]]

    def contagem(serie):
        s = serie.dropna().astype(str)
        return [{"valor": k, "posts": int(v), "pct": round(v / len(s), 4)} for k, v in s.value_counts().items()]

    video = cat[cat["tipo_post"].isin(["reels", "short", "video"])]
    ranking = cat.sort_values("lift", ascending=False)
    perfis = json.loads(ACHADOS.read_text(encoding="utf-8")).get("perfis_destaque", []) if ACHADOS.exists() else []
    return {
        "numeros": {
            "publicacoes": int(len(base)),
            "com_metrica": int(len(validos)),
            "top_categorizadas": int(len(cat)),
            "perfis": int(base["perfil"].nunique()),
            "instagram": int((base["plataforma"] == "instagram").sum()),
            "youtube": int((base["plataforma"] == "youtube").sum()),
            "inicio": str(base["publicado_em"].min())[:10],
            "fim": str(base["publicado_em"].max())[:10],
        },
        "tema": contagem(cat["tema_principal"]),
        "formato": contagem(video["formato_video"]),
        "hook": contagem(cat["tipo_hook"]),
        "n_video": int(len(video)),
        "ranking": [_detalhe(r, midia) for r in ranking.to_dict("records")],
        "perfis_destaque": perfis,
    }


@app.get("/api/exemplos")
def exemplos():
    return [
        {"titulo": "Análise de alimentação", "mode": "analisar",
         "query": "Quais formatos e ganchos mais aparecem nas publicações de alto desempenho de pequenos negócios de alimentação?",
         "segment": "alimentacao"},
        {"titulo": "Salões de beleza", "mode": "recomendar",
         "query": "Como a Stone pode aumentar o engajamento de salões de beleza no Instagram?",
         "segment": "beleza", "filters": {"plataforma": "instagram"}},
        {"titulo": "Reels para restaurantes", "mode": "gerar_criativo",
         "query": "Preciso de um Reels para atrair donos de pequenos restaurantes",
         "segment": "alimentacao", "filters": {"tipo_post": "reels"}, "n_criativos": 1},
    ]


if MIDIA.exists():
    app.mount("/midia", StaticFiles(directory=MIDIA), name="midia")
app.mount("/static", StaticFiles(directory=ESTATICO), name="static")


@app.get("/")
def pagina():
    return FileResponse(ESTATICO / "index.html")


if __name__ == "__main__":
    import uvicorn

    porta = int(os.getenv("PORTA_FRONTEND", "8000"))
    url = f"http://127.0.0.1:{porta}"
    print(f"Jade em {url}  (Ctrl+C para parar)")
    carregar()
    if os.getenv("ABRIR_NAVEGADOR", "1") != "0":
        threading.Timer(1.5, lambda: webbrowser.open(url)).start()
    uvicorn.run(app, host="127.0.0.1", port=porta, log_level="warning")
