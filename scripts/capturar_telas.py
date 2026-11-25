"""
Captura as telas do frontend para docs/img.

A API real é usada, mas a função executar é trocada por uma que devolve execuções reais já gravadas
em outputs/execucoes/execucoes.jsonl, então nenhuma chamada ao modelo é feita.

Requer playwright e o Chromium (pip install playwright e playwright install chromium).

Uso (na raiz do repositório)
    python scripts/capturar_telas.py
"""
import json
import sys
import threading
import time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

import uvicorn  # noqa: E402
from playwright.sync_api import sync_playwright  # noqa: E402

import backend.api.main as appmod  # noqa: E402
from backend.config import OUT_EXECUCOES  # noqa: E402
from backend.schemas.contrato import Saida  # noqa: E402

REGS = [json.loads(linha) for linha in (OUT_EXECUCOES / "execucoes.jsonl").read_text(encoding="utf-8").splitlines()]
ESTADO = {"limite": False}


def replay(entrada):
    e = entrada.model_dump()
    alvo = None
    for r in REGS:
        re_ = r["entrada"]
        if (re_["mode"], re_["query"], re_.get("segment"), re_["filters"]) == (e["mode"], e["query"], e.get("segment"), e["filters"]):
            if ESTADO["limite"] and r["erros"]:
                alvo = r
            elif not ESTADO["limite"] and not r["erros"] and (r["saida"]["creatives"] or e["mode"] != "gerar_criativo"):
                alvo = r
    if alvo is None:
        raise RuntimeError(f"sem execução gravada para {e['mode']} {e['query'][:40]}")
    if ESTADO["limite"]:
        appmod._ocorrencias["limite"] = 30.0
    return Saida.model_validate(alvo["saida"])


appmod.executar = replay
PORTA = 8765
threading.Thread(target=lambda: uvicorn.run(appmod.app, host="127.0.0.1", port=PORTA, log_level="warning"), daemon=True).start()
time.sleep(4)

OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "docs" / "img"
OUT.mkdir(parents=True, exist_ok=True)


def exemplo(page, i):
    page.locator("#exemplos-iniciais .exemplo").nth(i).click()
    page.wait_for_selector("#saida .cabecalho-resultado", timeout=20000)
    page.wait_for_timeout(1200)


with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=1.5)
    url = f"http://127.0.0.1:{PORTA}/"

    page.goto(url); page.wait_for_selector(".vitrine__item img"); page.wait_for_timeout(1500)
    page.screenshot(path=OUT / "00_inicio.png", full_page=True)

    exemplo(page, 2)
    page.locator(".criativo").first.screenshot(path=OUT / "01_criativo.png")

    page.locator(".criativo__fontes .cita").first.click(); page.wait_for_timeout(700)
    page.locator("section.bloco", has=page.locator("#ref-titulo")).screenshot(path=OUT / "02_referencias.png")
    page.locator("section.bloco", has=page.locator("#ach-titulo")).screenshot(path=OUT / "03_achados.png")

    page.goto(url); page.wait_for_selector(".vitrine__item img")
    exemplo(page, 1)
    page.locator("#resultado").screenshot(path=OUT / "04_recomendar.png")

    page.goto(url); page.wait_for_selector(".vitrine__item img")
    exemplo(page, 0)
    page.locator("section.bloco", has=page.locator("#exp-titulo")).screenshot(path=OUT / "05_analisar.png")

    page.goto(url); page.wait_for_selector(".vitrine__item img")
    page.fill("#query", "criptomoedas e blockchain")
    page.check("input[value=analisar]")
    page.click("#enviar"); page.wait_for_selector("#saida .vazio"); page.wait_for_timeout(500)
    page.locator("#saida").screenshot(path=OUT / "06_sem_resultado.png")

    ESTADO["limite"] = True
    page.goto(url); page.wait_for_selector(".vitrine__item img")
    exemplo(page, 2)
    page.locator("#saida .aviso--erro").screenshot(path=OUT / "07_limite_429.png")
    ESTADO["limite"] = False

    page.goto(url); page.click("#aba-base"); page.wait_for_selector(".numeros"); page.wait_for_timeout(1500)
    page.screenshot(path=OUT / "08_visao_da_base.png", full_page=False)
    page.locator("section.bloco", has=page.locator("#rk-titulo")).screenshot(path=OUT / "09_ranking.png")
    b.close()
print("ok", sorted(x.name for x in OUT.iterdir()))
