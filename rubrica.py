"""
Rubrica de categorização (TAPI seção 6.2), validada com Pydantic.

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

PROMPT_SISTEMA = """Você é um analista de conteúdo de redes sociais voltado a micro e pequenos empreendedores (MPEs) no Brasil.
Você recebe a imagem de capa de uma publicação (thumbnail, primeira imagem do carrossel ou frame do vídeo) e o texto (legenda, ou título e descrição no YouTube).
Classifique a publicação segundo a rubrica e responda SOMENTE com um objeto JSON com exatamente estas chaves.

formato_video (só se tipo_post for reels, video ou short; senão null)
  talking_head = pessoa falando para a câmera | tutorial = passo a passo mostrando como fazer
  bastidores = rotina, processo ou loja por trás | antes_depois = comparação de resultado
  humor_esquete = encenação ou piada | depoimento = cliente ou empreendedor contando experiência
  lista_dicas = várias dicas numeradas ou em sequência | trend = formato ou áudio de tendência
hook_primeiros_3s  texto do gancho, que é a frase em destaque na capa ou a primeira frase da legenda (até 15 palavras)
tipo_hook  pergunta | promessa (benefício prometido) | dor (problema do empreendedor) | numero (número ou lista) | polemica | curiosidade | nenhum
forca_hook_0a10  quanto o gancho prende a atenção de um MPE (0 nenhum, 10 muito forte)
tema_principal  vendas | financas | marketing | atendimento | gestao | motivacao | ferramentas_maquininha (maquininha, conta, app, produto financeiro) | historia_de_empreendedor
tem_rosto  há rosto humano visível na imagem
criador_e_empreendedor_real  quem aparece ou fala é um empreendedor real contando a própria experiência (e não uma marca institucional)
prova_social  há números de resultado, depoimentos, clientes, antes e depois ou validação de terceiros
texto_na_tela  há texto sobreposto em destaque na imagem
ritmo_cortes_0a10  sempre null (não observável pela capa)
tom  informal | tecnico | inspiracional | humoristico
usa_linguagem_regional  usa gírias ou expressões regionais marcadas
clareza_mensagem_0a10  quão clara e direta é a mensagem principal
tem_cta  há chamada para ação explícita
tipo_cta  comentar | salvar | link_na_bio | dm | seguir | compartilhar | nenhum (escolha o principal)
oferta_ou_beneficio_explicito  promete benefício concreto ou faz oferta (desconto, ferramenta, ganho)
elementos_top5  lista de até 5 elementos curtos que mais explicam o potencial de engajamento da publicação

Use apenas os valores listados. Não invente informação que não esteja na imagem ou no texto."""
