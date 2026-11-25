"""
CLI do agente.

Uso (na raiz do repositório)
    python -m backend.run gerar_criativo "Preciso de um Reels para atrair donos de pequenos restaurantes"
    python -m backend.run analisar "Quais ganchos aparecem no top 10% de alimentação?"
"""
import json
import sys

from backend.graph.agente import executar


def main():
    q = " ".join(sys.argv[2:]) or "Preciso de um Reels para atrair donos de pequenos restaurantes"
    r = executar({"mode": sys.argv[1] if len(sys.argv) > 1 else "gerar_criativo", "query": q})
    print(json.dumps(r.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
