"""
Contrato da ferramenta (TAPI seção 7), usado pelo agente, pelo servidor MCP e pela API.

Entrada  mode, query, segment, filters (e n_criativos)
Saída    findings, reference_posts, creatives, recomendacoes, confidence_flag, explanation
"""
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field

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
