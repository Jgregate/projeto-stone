"""
Agente de conteúdo para MPEs (Stone · Inteli Academy).

Orquestrado com LangGraph. O LLM interpreta e redige; todos os números, exemplos e links
vêm da base coletada (data/categorias.parquet e data/base.parquet). Cada recomendação ou
criativo aponta para as publicações reais em que se apoia (rastreabilidade, TAPI seção 7).

Fluxo (grafo)
    interpretar  -> extrai filtros da pergunta (segmento, plataforma, tipo de post, tema), sem LLM
    consultar    -> ferramenta consultar_base: frequências da rubrica no top 10% filtrado
    referenciar  -> ferramenta buscar_referencias: publicações de alto desempenho mais parecidas
    redigir      -> LLM: análise (modo analisar) ou recomendações (modo recomendar)
    criar        -> ferramenta gerar_criativos: LLM gera gancho, roteiro, legenda e CTA (modo gerar_criativo)
    registrar    -> grava a execução em data/execucoes.jsonl

Contrato (TAPI seção 7), entrada e saída validadas com Pydantic
    entrada  mode (analisar | recomendar | gerar_criativo), query, segment, filters
    saída    findings, reference_posts, creatives, confidence_flag, explanation

Uso como função
    from agente import executar
    r = executar({"mode": "gerar_criativo", "query": "Reels para donos de pequenos restaurantes"})
"""
import json
import os
import re
import time
import unicodedata
from datetime import datetime, timezone
from functools import lru_cache
from math import log1p
from pathlib import Path
from typing import Dict, List, Literal, Optional, TypedDict

import pandas as pd
import requests
from dotenv import load_dotenv
from langgraph.graph import END, StateGraph
from pydantic import BaseModel, Field, ValidationError

load_dotenv()

DATA = Path(__file__).parent / "data"
LOG = DATA / "execucoes.jsonl"
URL = "https://api.groq.com/openai/v1/chat/completions"
MODELO_LLM = os.getenv("GROQ_AGENT_MODEL", "openai/gpt-oss-120b")
MIN_CONFIANCA = 10
MIN_SUBCONJUNTO = 15

# --------------------------------------------------------------------------- contrato

Modo = Literal["analisar", "recomendar", "gerar_criativo"]


class Filtros(BaseModel):
    plataforma: Optional[Literal["instagram", "youtube"]] = None
    tipo_post: Optional[Literal["reels", "carrossel", "imagem", "short", "video"]] = None
    faixa: Optional[Literal["micro", "medio", "grande"]] = None
    tema_principal: Optional[str] = None


class Entrada(BaseModel):
    mode: Modo
    query: str
    segment: Optional[str] = Field(None, description="alimentacao, beleza, varejo, financas, gestao, marketing...")
    filters: Filtros = Field(default_factory=Filtros)
    n_criativos: int = Field(1, ge=1, le=5)


class Achado(BaseModel):
    campo: str
    valor: str
    posts: int
    pct: float
    razao_top_base: Optional[float] = None
    confidence_flag: bool


class PostReferencia(BaseModel):
    post_id: str
    perfil: str
    plataforma: str
    tipo_post: str
    url: str
    engajamento: float
    lift: float
    tema_principal: Optional[str] = None
    tipo_hook: Optional[str] = None
    formato_video: Optional[str] = None
    gancho: Optional[str] = None


class Cena(BaseModel):
    tempo: str
    acao: str


class Criativo(BaseModel):
    titulo: str
    formato: str
    gancho: str
    roteiro: List[Cena]
    legenda: str
    cta: str
    inspirado_em: List[str] = Field(description="post_ids das publicações de referência")
    justificativa: str


class Saida(BaseModel):
    mode: Modo
    query: str
    filtros_aplicados: Dict[str, Optional[str]]
    n_posts_analisados: int
    findings: List[Achado]
    reference_posts: List[PostReferencia]
    creatives: List[Criativo] = []
    recomendacoes: List[str] = []
    confidence_flag: bool
    explanation: str


# --------------------------------------------------------------------------- dados

def _norm(t):
    t = unicodedata.normalize("NFKD", str(t or "")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]", " ", t)


@lru_cache(maxsize=1)
def carregar():
    cat = pd.read_parquet(DATA / "categorias.parquet")
    base = pd.read_parquet(DATA / "base.parquet")
    cat["_busca"] = (cat["texto"].fillna("") + " " + cat["hook_primeiros_3s"].fillna("") + " "
                     + cat["elementos_top5"].fillna("").str.replace("|", " ") + " "
                     + cat["tema_principal"].fillna("") + " " + cat["segmento"].fillna("")).map(_norm)
    return cat, base


SEGMENTOS = {
    "alimentacao": ["restaurante", "confeitaria", "comida", "delivery", "marmita", "doce", "bolo", "lanchonete",
                    "padaria", "hamburguer", "food", "cozinha", "brownie", "alimentacao", "bar"],
    "beleza": ["salao", "manicure", "estetica", "cabelo", "barbearia", "beleza", "unha", "maquiagem", "cabeleireir"],
    "varejo": ["loja", "roupa", "moda", "revenda", "revendedora", "varejo", "boutique", "vitrine", "e commerce"],
    "financas": ["financas", "dinheiro", "caixa", "lucro", "precificacao", "preco", "divida", "credito", "juros"],
    "gestao": ["gestao", "mei", "nota fiscal", "imposto", "tributaria", "contabil", "estoque", "organizar"],
    "marketing": ["marketing", "instagram", "seguidores", "anuncio", "trafego", "divulgar", "conteudo"],
}
TEMAS = ["vendas", "financas", "marketing", "atendimento", "gestao", "motivacao", "ferramentas_maquininha",
         "historia_de_empreendedor"]


def interpretar_query(entrada: Entrada):
    q = _norm(entrada.query)
    f = entrada.filters.model_dump()
    seg = entrada.segment
    if not seg:
        for s, chaves in SEGMENTOS.items():
            if any(k in q for k in chaves):
                seg = s
                break
    if not f.get("plataforma"):
        f["plataforma"] = "youtube" if ("youtube" in q or "shorts" in q) else ("instagram" if "instagram" in q else None)
    if not f.get("tipo_post"):
        for t, k in [("reels", "reels"), ("reels", "reel"), ("carrossel", "carrossel"), ("short", "shorts"),
                     ("imagem", "post estatico"), ("imagem", "imagem")]:
            if k in q:
                f["tipo_post"] = t
                break
    if not f.get("faixa"):
        for fx, k in [("micro", "micro"), ("micro", "pequeno perfil"), ("grande", "grande perfil")]:
            if k in q:
                f["faixa"] = fx
    return seg, f


def filtrar(df, seg, f, relaxar=True):
    """Aplica os filtros; se sobrar pouco, relaxa do mais específico para o mais geral."""
    ordem = ["faixa", "tema_principal", "tipo_post", "plataforma"]
    ativos = {k: v for k, v in f.items() if v}
    seg_ativo = seg
    relaxados = []

    def aplicar(ativos, seg_ativo):
        d = df
        for k, v in ativos.items():
            if k in d.columns:
                d = d[d[k] == v]
        if seg_ativo:
            # segmento do perfil OU o texto do post menciona o segmento
            chaves = SEGMENTOS.get(seg_ativo, [seg_ativo])
            mask = (d["segmento"] == seg_ativo) | d["_busca"].str.contains("|".join(chaves), regex=True)
            d = d[mask]
        return d

    d = aplicar(ativos, seg_ativo)
    while relaxar and len(d) < MIN_SUBCONJUNTO and (ativos or seg_ativo):
        k = next((k for k in ordem if k in ativos), None)
        if k:
            relaxados.append(k)
            ativos.pop(k)
        else:
            relaxados.append("segmento")
            seg_ativo = None
        d = aplicar(ativos, seg_ativo)
    return d, {**{k: ativos.get(k) for k in ordem}, "segmento": seg_ativo}, relaxados


# --------------------------------------------------------------------------- ferramentas

CAMPOS_ACHADOS = ["tipo_post", "formato_video", "tipo_hook", "tema_principal", "tom", "tem_rosto",
                  "texto_na_tela", "tem_cta", "tipo_cta", "oferta_ou_beneficio_explicito", "legenda_tamanho"]


def consultar_base(seg=None, filtros=None, top_n=3):
    """Frequências da rubrica no top 10% filtrado, com razão top/base para tipo de post."""
    cat, base = carregar()
    sub, aplicados, relaxados = filtrar(cat, seg, filtros or {})
    achados = []
    for campo in CAMPOS_ACHADOS:
        s = sub[campo]
        if campo == "formato_video":
            s = s[sub["tipo_post"].isin(["reels", "short", "video"])]
        s = s.dropna().astype(str)
        if s.empty:
            continue
        cont = s.value_counts()
        for valor, n in cont.head(top_n).items():
            razao = None
            if campo == "tipo_post":
                b = base[base["metrica_valida"]]
                if aplicados.get("plataforma"):
                    b = b[b["plataforma"] == aplicados["plataforma"]]
                pb = (b["tipo_post"] == valor).mean()
                razao = round((n / len(s)) / pb, 2) if pb else None
            achados.append(Achado(campo=campo, valor=valor, posts=int(n), pct=round(n / len(s), 3),
                                  razao_top_base=razao, confidence_flag=bool(n < MIN_CONFIANCA)))
    return sub, aplicados, relaxados, achados


def buscar_referencias(sub, query, k=5):
    """Publicações de alto desempenho mais próximas da pergunta (palavras em comum x lift)."""
    termos = [t for t in _norm(query).split() if len(t) > 3]
    if sub.empty:
        return []
    sc = sub["_busca"].apply(lambda b: sum(t in b for t in termos))
    rank = sub.assign(_score=(sc + 1) * sub["lift"].fillna(0).map(log1p)).sort_values("_score", ascending=False)
    rank = rank.drop_duplicates("perfil").head(k) if rank["perfil"].nunique() >= k else rank.head(k)
    return [PostReferencia(
        post_id=r.post_id, perfil=r.perfil, plataforma=r.plataforma, tipo_post=r.tipo_post, url=r.url,
        engajamento=round(float(r.engajamento), 5), lift=round(float(r.lift), 2),
        tema_principal=r.tema_principal, tipo_hook=r.tipo_hook,
        formato_video=r.formato_video if isinstance(r.formato_video, str) else None,
        gancho=r.hook_primeiros_3s) for r in rank.itertuples()]


def _llm(sistema, usuario, max_tokens=2500):
    chave = os.getenv("GROQ_API_KEY")
    if not chave:
        raise RuntimeError("GROQ_API_KEY ausente")
    payload = {"model": MODELO_LLM, "temperature": 0.4, "response_format": {"type": "json_object"},
               "max_completion_tokens": max_tokens,
               "messages": [{"role": "system", "content": sistema}, {"role": "user", "content": usuario}]}
    if "gpt-oss" in MODELO_LLM:
        payload["reasoning_effort"] = "low"
    for tentativa in range(6):
        r = requests.post(URL, headers={"Authorization": f"Bearer {chave}"}, json=payload, timeout=180)
        if r.status_code == 429:
            espera = float(r.headers.get("retry-after", 15 * (tentativa + 1)))
            if espera > 300:
                raise RuntimeError("limite diário do Groq atingido para o modelo do agente")
            time.sleep(espera + 1)
            continue
        if r.status_code == 400 and "reasoning" in r.text and "reasoning_effort" in payload:
            payload.pop("reasoning_effort")
            continue
        if r.status_code >= 400:
            raise RuntimeError(f"Groq {r.status_code} {r.text[:200]}")
        conteudo = r.json()["choices"][0]["message"]["content"] or "{}"
        return json.loads(conteudo)
    raise RuntimeError("limite do Groq persistente")


TOM_STONE = ("Tom de voz do Impulso Stone: próximo, acolhedor, educativo, encorajador, linguagem simples e direta, "
             "sem jargão e sem promessas exageradas. Público majoritariamente feminino, 35 a 54 anos, "
             "micro e pequenos empreendedores (lojistas, prestadores de serviço e autônomos).")


def _contexto(achados, refs):
    a = [f"- {x.campo} = {x.valor}: {x.posts} posts ({x.pct:.0%}){' [baixa confiança]' if x.confidence_flag else ''}"
         for x in achados]
    r = [f"- {p.post_id} | @{p.perfil} | {p.plataforma}/{p.tipo_post} | tema {p.tema_principal} | "
         f"gancho ({p.tipo_hook}): {p.gancho} | lift {p.lift}" for p in refs]
    return "ACHADOS DO TOP 10%\n" + "\n".join(a) + "\n\nPUBLICAÇÕES DE REFERÊNCIA\n" + "\n".join(r)


def gerar_criativos(query, achados, refs, n=1):
    sistema = ("Você é estrategista de conteúdo da Stone para micro e pequenos empreendedores. "
               + TOM_STONE + " Crie criativos para Instagram (Reels ou carrossel) inspirados nos padrões observados "
               "e nas publicações de referência. Use apenas padrões que aparecem nos achados. "
               "Responda SOMENTE em JSON no formato {\"criativos\": [ ... ]}, cada criativo com as chaves "
               "titulo, formato, gancho (até 12 palavras), roteiro (lista de {tempo, acao}, 30 a 45 s no total), "
               "legenda (até 400 caracteres), cta, inspirado_em (lista de post_id das referências usadas, "
               "obrigatoriamente da lista recebida) e justificativa (cite os achados que sustentam a escolha).")
    usuario = f"PEDIDO\n{query}\n\nQUANTIDADE\n{n}\n\n{_contexto(achados, refs)}"
    bruto = _llm(sistema, usuario)
    ids = {p.post_id for p in refs}
    out = []
    for c in bruto.get("criativos", [])[:n]:
        try:
            cr = Criativo.model_validate(c)
        except ValidationError:
            continue
        cr.inspirado_em = [i for i in cr.inspirado_em if i in ids] or [refs[0].post_id]
        out.append(cr)
    return out


def redigir(mode, query, achados, refs, aplicados, relaxados):
    pede = ("uma análise objetiva dos padrões" if mode == "analisar"
            else "de 3 a 5 recomendações práticas e acionáveis para a Stone")
    sistema = ("Você é analista de conteúdo da Stone. " + TOM_STONE + " Escreva " + pede + " com base SOMENTE nos "
               "achados e publicações fornecidos, citando números e post_ids. Trate os achados como padrões observados, "
               "não como garantia de resultado. Responda em JSON {\"explicacao\": str, \"recomendacoes\": [str]}.")
    usuario = (f"PERGUNTA\n{query}\n\nFILTROS APLICADOS\n{aplicados}\nFILTROS RELAXADOS POR FALTA DE DADOS\n{relaxados}\n\n"
               + _contexto(achados, refs))
    out = _llm(sistema, usuario, max_tokens=1800)
    return str(out.get("explicacao", "")), [str(r) for r in out.get("recomendacoes", [])]


def explicacao_padrao(achados, n, aplicados, relaxados):
    principais = {}
    for a in achados:
        principais.setdefault(a.campo, a)
    partes = [f"{c} mais frequente = {a.valor} ({a.pct:.0%})" for c, a in principais.items()]
    txt = f"Entre {n} publicações de alto desempenho (filtros {aplicados}), " + "; ".join(partes[:6]) + "."
    if relaxados:
        txt += f" Filtros relaxados por falta de dados: {', '.join(relaxados)}."
    return txt


# --------------------------------------------------------------------------- grafo

class Estado(TypedDict, total=False):
    entrada: Entrada
    segmento: Optional[str]
    filtros: dict
    sub: object
    aplicados: dict
    relaxados: list
    achados: list
    refs: list
    criativos: list
    recomendacoes: list
    explicacao: str
    erros: list


def no_interpretar(s: Estado):
    seg, f = interpretar_query(s["entrada"])
    return {"segmento": seg, "filtros": f, "erros": []}


def no_consultar(s: Estado):
    sub, aplicados, relaxados, achados = consultar_base(s["segmento"], s["filtros"])
    return {"sub": sub, "aplicados": aplicados, "relaxados": relaxados, "achados": achados}


def no_referenciar(s: Estado):
    k = 5 if s["entrada"].mode != "analisar" else 3
    return {"refs": buscar_referencias(s["sub"], s["entrada"].query, k=k)}


def no_redigir(s: Estado):
    e = s["entrada"]
    try:
        exp, recs = redigir(e.mode, e.query, s["achados"], s["refs"], s["aplicados"], s["relaxados"])
        return {"explicacao": exp, "recomendacoes": recs}
    except Exception as err:  # noqa: BLE001
        return {"explicacao": explicacao_padrao(s["achados"], len(s["sub"]), s["aplicados"], s["relaxados"]),
                "recomendacoes": [], "erros": s["erros"] + [f"redigir: {err}"]}


def no_criar(s: Estado):
    e = s["entrada"]
    try:
        cr = gerar_criativos(e.query, s["achados"], s["refs"], e.n_criativos)
    except Exception as err:  # noqa: BLE001
        return {"criativos": [], "erros": s["erros"] + [f"criar: {err}"]}
    exp = explicacao_padrao(s["achados"], len(s["sub"]), s["aplicados"], s["relaxados"])
    return {"criativos": cr, "explicacao": exp}


def rota(s: Estado):
    return "criar" if s["entrada"].mode == "gerar_criativo" else "redigir"


def montar_grafo():
    g = StateGraph(Estado)
    g.add_node("interpretar", no_interpretar)
    g.add_node("consultar", no_consultar)
    g.add_node("referenciar", no_referenciar)
    g.add_node("redigir", no_redigir)
    g.add_node("criar", no_criar)
    g.set_entry_point("interpretar")
    g.add_edge("interpretar", "consultar")
    g.add_edge("consultar", "referenciar")
    g.add_conditional_edges("referenciar", rota, {"criar": "criar", "redigir": "redigir"})
    g.add_edge("redigir", END)
    g.add_edge("criar", END)
    return g.compile()


GRAFO = None


def executar(entrada) -> Saida:
    """Função integrável: recebe dict ou Entrada e devolve Saida (Pydantic)."""
    global GRAFO
    e = entrada if isinstance(entrada, Entrada) else Entrada.model_validate(entrada)
    GRAFO = GRAFO or montar_grafo()
    ini = time.time()
    s = GRAFO.invoke({"entrada": e})
    achados = s["achados"]
    baixa = len(s["sub"]) < MIN_SUBCONJUNTO or bool(s["relaxados"]) or \
        any(a.confidence_flag for a in achados if a.campo in ("tipo_hook", "tema_principal", "formato_video"))
    saida = Saida(
        mode=e.mode, query=e.query, filtros_aplicados=s["aplicados"], n_posts_analisados=len(s["sub"]),
        findings=achados, reference_posts=s["refs"], creatives=s.get("criativos", []),
        recomendacoes=s.get("recomendacoes", []), confidence_flag=baixa, explanation=s.get("explicacao", ""))
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a", encoding="utf-8") as f:
        f.write(json.dumps({"executado_em": datetime.now(timezone.utc).isoformat(), "duracao_s": round(time.time() - ini, 1),
                            "modelo_llm": MODELO_LLM, "entrada": e.model_dump(), "erros": s.get("erros", []),
                            "saida": saida.model_dump()}, ensure_ascii=False) + "\n")
    return saida


if __name__ == "__main__":
    import sys
    q = " ".join(sys.argv[2:]) or "Preciso de um Reels para atrair donos de pequenos restaurantes"
    r = executar({"mode": sys.argv[1] if len(sys.argv) > 1 else "gerar_criativo", "query": q})
    print(json.dumps(r.model_dump(), ensure_ascii=False, indent=2))
