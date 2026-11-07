"""Baixa as bases públicas usadas no modelo da Luz Vital.

- ANEEL: Interrupções de Energia Elétrica nas Redes de Distribuição, um ZIP por ano (2019 a 2025)
  e os dois dicionários de dados em PDF.
- INMET: dados históricos horários, um ZIP por ano com todas as estações automáticas.

Os arquivos vão para dados/brutos/ (fora do git). Arquivo que já existe não é baixado de novo,
então dá para rodar quantas vezes quiser. Se algum download falhar, o script avisa e segue.

Uso:
    python baixar_dados.py            # tudo
    python baixar_dados.py --so aneel
    python baixar_dados.py --so inmet
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

import requests

RAIZ = Path(__file__).resolve().parent
BRUTOS = RAIZ / "dados" / "brutos"
ANOS = range(2019, 2026)

# Endereços tirados da API do catálogo da ANEEL (CKAN):
# https://dadosabertos.aneel.gov.br/api/3/action/package_show?id=interrupcoes-de-energia-eletrica-nas-redes-de-distribuicao
ANEEL_BASE = "https://dadosabertos.aneel.gov.br/dataset/ccb25653-f07b-4f28-84c2-62a89d1f5a56/resource"
ANEEL_ZIPS = {
    2019: "965d2abb-91fe-4fab-b463-8c84f2e02188",
    2020: "58201617-8364-4e7f-975d-21f8b8c7436f",
    2021: "42d778de-4a10-4b54-a00a-87c8ff35db6f",
    2022: "7d081751-3f4c-4ede-96b5-1bf2e46b61ca",
    2023: "cce72c2b-a4cb-4b98-818f-3ac56bbf2a78",
    2024: "cc091bb8-b308-46b2-98ec-c2fd58e7194b",
    2025: "1aa6ad85-05b8-4471-9ca4-316566214ba9",
}
ANEEL_DICIONARIOS = {
    "dicionario-ate-dez2025.pdf": "101e4650-6a02-4f1f-8034-4c267b1ea462",
    "dicionario-a-partir-jan2026.pdf": "6e5611de-948d-4473-b309-520d7523b762",
}
ANEEL_PDF = "dm-interrupcoes-de-energia-eletrica-nas-redes-de-distribuicao.pdf"

INMET_URL = "https://portal.inmet.gov.br/uploads/dadoshistoricos/{ano}.zip"


def baixar(url: str, destino: Path) -> bool:
    if destino.exists() and destino.stat().st_size > 0:
        print(f"  já existe: {destino.relative_to(RAIZ)}")
        return True
    destino.parent.mkdir(parents=True, exist_ok=True)
    parcial = destino.with_suffix(destino.suffix + ".parcial")
    try:
        with requests.get(url, stream=True, timeout=60) as r:
            r.raise_for_status()
            total = int(r.headers.get("content-length") or 0)
            feito = 0
            with open(parcial, "wb") as f:
                for bloco in r.iter_content(chunk_size=1 << 20):
                    f.write(bloco)
                    feito += len(bloco)
                    if total:
                        print(f"\r  {destino.name}: {feito / total:6.1%} de {total / 1e6:.0f} MB", end="")
        print()
        parcial.replace(destino)
        return True
    except requests.RequestException as e:
        print(f"\n  FALHOU {url}: {e}")
        parcial.unlink(missing_ok=True)
        return False


def baixar_aneel() -> list[str]:
    print("ANEEL")
    falhas = []
    pasta = BRUTOS / "aneel"
    for nome, rid in ANEEL_DICIONARIOS.items():
        if not baixar(f"{ANEEL_BASE}/{rid}/download/{ANEEL_PDF}", pasta / nome):
            falhas.append(nome)
    for ano, rid in ANEEL_ZIPS.items():
        nome = f"interrupcoes-energia-eletrica-{ano}.zip"
        if not baixar(f"{ANEEL_BASE}/{rid}/download/{nome}", pasta / nome):
            falhas.append(nome)
    return falhas


def baixar_inmet() -> list[str]:
    print("INMET")
    falhas = []
    for ano in ANOS:
        if not baixar(INMET_URL.format(ano=ano), BRUTOS / "inmet" / f"{ano}.zip"):
            falhas.append(f"{ano}.zip")
    if falhas:
        print(
            "  O portal do INMET às vezes recusa clientes automáticos. Se falhar, baixe no navegador\n"
            "  em https://portal.inmet.gov.br/dadoshistoricos e salve como dados/brutos/inmet/<ano>.zip."
        )
    return falhas


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--so", choices=["aneel", "inmet"])
    args = p.parse_args()

    falhas = []
    if args.so in (None, "aneel"):
        falhas += baixar_aneel()
    if args.so in (None, "inmet"):
        falhas += baixar_inmet()

    (BRUTOS / "DATA_DOWNLOAD.txt").write_text(f"Última execução de baixar_dados.py: {date.today()}\n", encoding="utf-8")
    if falhas:
        print(f"\n{len(falhas)} arquivo(s) não baixado(s): {', '.join(falhas)}")
        return 1
    print("\nTudo baixado.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
