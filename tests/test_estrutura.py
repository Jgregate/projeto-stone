"""Caminhos da nova estrutura de pastas e arquivos de dados versionados."""
from backend import config


def test_pastas_de_dados_existem():
    for pasta in [config.PROCESSED, config.PERFIS, config.VALIDACAO, config.MODELOS, config.OUT_ANALISE,
                  config.OUT_COLETA, config.OUT_EXECUCOES, config.FRONTEND]:
        assert pasta.is_dir(), pasta


def test_arquivos_usados_pelo_agente_e_pela_api():
    for arq in [config.PROCESSED / "base.parquet", config.PROCESSED / "categorias.parquet",
                config.OUT_ANALISE / "achados.json", config.FRONTEND / "index.html",
                config.MODELOS / "haarcascade_frontalface_default.xml", config.PERFIS / "perfis.csv"]:
        assert arq.is_file(), arq


def test_modulos_importam():
    import backend.analysis.analisar_top  # noqa: F401
    import backend.analysis.montar_base  # noqa: F401
    import backend.api.main  # noqa: F401
    import backend.categorization.categorizar  # noqa: F401
    import backend.categorization.categorizar_texto  # noqa: F401
    import backend.mcp_server.servidor  # noqa: F401
    import backend.validation.anotar  # noqa: F401
    import backend.validation.validacao  # noqa: F401
