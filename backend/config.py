"""
Caminhos e configuração comuns a todo o backend.

Todos os scripts usam estes caminhos absolutos, então funcionam a partir de qualquer pasta.
As variáveis de ambiente ficam no .env da raiz (modelo em .env.example).
"""
from pathlib import Path

from dotenv import load_dotenv

RAIZ = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ / ".env")

# dados
DATA = RAIZ / "data"
RAW = DATA / "raw"                       # fora do git
RAW_INSTAGRAM = RAW / "instagram"        # respostas brutas do Business Discovery (cache)
RAW_YOUTUBE = RAW / "youtube"            # respostas brutas da YouTube Data API (cache)
MIDIA = RAW / "midia"                    # capas das publicações do top 10%
PROCESSED = DATA / "processed"           # base, ranking, categorias e caches do modelo
PERFIS = DATA / "perfis"                 # listas de perfis e canais
VALIDACAO = DATA / "validacao"           # anotação manual
MODELOS = DATA / "modelos"               # detector de rostos do OpenCV

# saídas
OUTPUTS = RAIZ / "outputs"
OUT_COLETA = OUTPUTS / "coleta"
OUT_ANALISE = OUTPUTS / "analise"
OUT_VALIDACAO = OUTPUTS / "validacao"
OUT_DEMO = OUTPUTS / "demo"
OUT_PLAYBOOK = OUTPUTS / "playbook"
OUT_EXECUCOES = OUTPUTS / "execucoes"

# interface
FRONTEND = RAIZ / "frontend"
