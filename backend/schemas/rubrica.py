"""
Rubrica de categorização (TAPI seção 6.2), validada com Pydantic.
O prompt correspondente fica em backend/prompts/rubrica.py.

Nível 1 (legenda + imagem de capa). Campos que dependem de assistir ao vídeo
(ritmo de cortes) ficam nulos e são declarados no README como fora do Nível 1.
legenda_tamanho, tipo_post e duracao_faixa são calculados de forma determinística, sem LLM.
"""
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

FORMATOS = Literal[
    "talking_head", "tutorial", "bastidores", "antes_depois",
    "humor_esquete", "depoimento", "lista_dicas", "trend",
]
TIPOS_HOOK = Literal["pergunta", "promessa", "dor", "numero", "polemica", "curiosidade", "nenhum"]
TEMAS = Literal[
    "vendas", "financas", "marketing", "atendimento", "gestao",
    "motivacao", "ferramentas_maquininha", "historia_de_empreendedor",
]
TONS = Literal["informal", "tecnico", "inspiracional", "humoristico"]
TIPOS_CTA = Literal["comentar", "salvar", "link_na_bio", "dm", "seguir", "compartilhar", "nenhum"]


class Rubrica(BaseModel):
    # Formato
    formato_video: Optional[FORMATOS] = Field(
        None, description="só para reels/short; null para imagem e carrossel")
    # Gancho
    hook_primeiros_3s: str = Field(
        description="gancho textual: texto em destaque na capa ou primeira frase da legenda (até 15 palavras)")
    tipo_hook: TIPOS_HOOK
    forca_hook_0a10: int = Field(ge=0, le=10)
    # Tema
    tema_principal: TEMAS
    # Pessoas
    tem_rosto: bool
    criador_e_empreendedor_real: bool
    prova_social: bool
    # Texto e edição
    texto_na_tela: bool
    ritmo_cortes_0a10: Optional[int] = Field(None, ge=0, le=10, description="Nível 2; null no Nível 1")
    # Linguagem
    tom: TONS
    usa_linguagem_regional: bool
    clareza_mensagem_0a10: int = Field(ge=0, le=10)
    # Conversão
    tem_cta: bool
    tipo_cta: TIPOS_CTA
    oferta_ou_beneficio_explicito: bool
    # Síntese
    elementos_top5: List[str] = Field(max_length=5)

    @field_validator("hook_primeiros_3s")
    @classmethod
    def corta_hook(cls, v):
        return " ".join(v.split()[:20])


CAMPOS_CATEGORICOS = [
    "formato_video", "tipo_hook", "tema_principal", "tem_rosto", "criador_e_empreendedor_real",
    "prova_social", "texto_na_tela", "tom", "usa_linguagem_regional", "tem_cta", "tipo_cta",
    "oferta_ou_beneficio_explicito",
]
CAMPOS_NOTA = ["forca_hook_0a10", "clareza_mensagem_0a10"]
CAMPOS_VALIDACAO = [
    "formato_video", "tipo_hook", "tema_principal", "tem_rosto", "texto_na_tela",
    "tom", "tem_cta", "tipo_cta",
]


# Rubrica da categorização híbrida (só texto, em lotes), usada por backend/categorization/categorizar_texto.py
class RubricaTexto(BaseModel):
    id: str
    formato_video: Optional[FORMATOS] = None
    hook_primeiros_3s: str
    tipo_hook: TIPOS_HOOK
    forca_hook_0a10: int = Field(ge=0, le=10)
    tema_principal: TEMAS
    criador_e_empreendedor_real: bool
    prova_social: bool
    tom: TONS
    usa_linguagem_regional: bool
    clareza_mensagem_0a10: int = Field(ge=0, le=10)
    tem_cta: bool
    tipo_cta: TIPOS_CTA
    oferta_ou_beneficio_explicito: bool
    elementos_top5: List[str] = Field(max_length=5)


class Lote(BaseModel):
    resultados: List[RubricaTexto]
