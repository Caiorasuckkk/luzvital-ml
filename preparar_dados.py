"""Monta a tabela diária a partir dos arquivos brutos (rode baixar_dados.py antes).

Saídas em dados/processados/:
- aneel_diario.csv  interrupções NÃO programadas da Enel SP agregadas por dia de início
- inmet_diario.csv  estação A701 (São Paulo - Mirante de Santana) agregada por dia
- diario.csv        as duas juntas, um dia por linha (é a tabela que o notebook usa)

Os ZIPs da ANEEL são nacionais e têm ~2,4 GB de CSV por ano, por isso a leitura é em pedaços
e só com as colunas necessárias. Os nomes das colunas seguem o dicionário de dados da ANEEL
(versão "dados até dez/2025") conferidos no cabeçalho dos arquivos.

Uso:
    python preparar_dados.py            # ANEEL + INMET + junção
    python preparar_dados.py --so aneel
    python preparar_dados.py --so inmet
"""

from __future__ import annotations

import argparse
import io
import sys
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parent
BRUTOS = RAIZ / "dados" / "brutos"
PROC = RAIZ / "dados" / "processados"
ANOS = range(2019, 2026)

# Enel Distribuição São Paulo (antiga Eletropaulo). O filtro é pelo CNPJ porque a sigla
# do agente pode mudar ao longo dos anos; as siglas encontradas são impressas para conferência.
CNPJ_ENEL_SP = "61695227000193"
COLS_ANEEL = [
    "DscTipoInterrupcao",
    "IdeMotivoInterrupcao",
    "DatInicioInterrupcao",
    "NumUnidadeConsumidora",
    "SigAgente",
    "NomAgenteRegulado",
    "NumCPFCNPJ",
]

ESTACAO = "A701"


def processar_aneel_ano(ano: int) -> tuple[pd.DataFrame, dict]:
    caminho = BRUTOS / "aneel" / f"interrupcoes-energia-eletrica-{ano}.zip"
    partes = []
    agentes: dict = {}
    with zipfile.ZipFile(caminho) as z:
        nome = next(n for n in z.namelist() if n.lower().endswith(".csv"))
        with z.open(nome) as f:
            leitor = pd.read_csv(f, sep=";", usecols=COLS_ANEEL, dtype=str, chunksize=2_000_000, encoding="utf-8")
            for ch in leitor:
                ch = ch[ch["NumCPFCNPJ"].str.strip() == CNPJ_ENEL_SP]
                if ch.empty:
                    continue
                for (sig, nom), n in ch.groupby(["SigAgente", "NomAgenteRegulado"]).size().items():
                    chave = (sig.strip(), nom.strip())
                    agentes[chave] = agentes.get(chave, 0) + n
                ch = ch[ch["DscTipoInterrupcao"].str.strip() == "Não Programada"]
                partes.append(
                    pd.DataFrame(
                        {
                            "data": pd.to_datetime(ch["DatInicioInterrupcao"].str[:10], format="%Y-%m-%d"),
                            "ucs": pd.to_numeric(ch["NumUnidadeConsumidora"], errors="coerce").fillna(0),
                            "dia_critico": ch["IdeMotivoInterrupcao"].str.strip() == "6",
                        }
                    )
                )
    df = pd.concat(partes, ignore_index=True)
    return df, agentes


def processar_aneel() -> pd.DataFrame:
    print("ANEEL: lendo os ZIPs em pedaços (filtro: CNPJ da Enel SP, só 'Não Programada')")
    diarios = []
    for ano in ANOS:
        df, agentes = processar_aneel_ano(ano)
        print(f"  {ano}: {len(df):>9,} interrupções não programadas | agente(s): {agentes}")
        df["ucs_dia_critico"] = df["ucs"].where(df["dia_critico"], 0)
        d = df.groupby("data").agg(
            ucs_atingidas=("ucs", "sum"),
            n_interrupcoes=("ucs", "size"),
            ucs_expurgo_dia_critico=("ucs_dia_critico", "sum"),
        )
        diarios.append(d)
    diario = pd.concat(diarios).groupby(level=0).sum()
    # Interrupção que começou em 31/12 do ano anterior pode aparecer no arquivo do ano seguinte e
    # vice-versa; o groupby acima já soma. Dias sem nenhuma interrupção ficam com zero.
    idx = pd.date_range(f"{ANOS[0]}-01-01", f"{ANOS[-1]}-12-31", freq="D", name="data")
    diario = diario.reindex(idx, fill_value=0).astype("int64")
    PROC.mkdir(parents=True, exist_ok=True)
    diario.to_csv(PROC / "aneel_diario.csv")
    print(f"  salvo em dados/processados/aneel_diario.csv ({len(diario)} dias)")
    return diario


def _coluna(df: pd.DataFrame, *trechos: str) -> str:
    """Acha a coluna cujo nome (em maiúsculas) contém todos os trechos. Falha se não achar ou se for ambíguo."""
    achadas = [c for c in df.columns if all(t in c.upper() for t in trechos)]
    if len(achadas) != 1:
        raise KeyError(f"Coluna com {trechos} não encontrada de forma única. Achadas: {achadas}")
    return achadas[0]


def ler_inmet_ano(ano: int) -> pd.DataFrame:
    caminho = BRUTOS / "inmet" / f"{ano}.zip"
    with zipfile.ZipFile(caminho) as z:
        nomes = [n for n in z.namelist() if f"_{ESTACAO}_" in n.upper()]
        if len(nomes) != 1:
            raise FileNotFoundError(f"{caminho.name}: esperava 1 arquivo da estação {ESTACAO}, achei {nomes}")
        bruto = z.read(nomes[0]).decode("latin-1")
    # 8 linhas de metadados da estação antes do cabeçalho
    df = pd.read_csv(io.StringIO(bruto), sep=";", skiprows=8, decimal=",", dtype=str)
    df = df.loc[:, ~df.columns.str.startswith("Unnamed")]

    col_data, col_hora = df.columns[0], df.columns[1]  # "Data" e "Hora UTC" (nomes variam entre anos)
    if not (col_data.upper().startswith("DATA") and col_hora.upper().startswith("HORA")):
        raise KeyError(f"{caminho.name}: esperava Data e Hora nas 2 primeiras colunas, achei {col_data!r}, {col_hora!r}")
    mapa = {
        "chuva_mm": _coluna(df, "PRECIPITA"),
        "pressao_mb": _coluna(df, "PRESSAO ATMOSFERICA AO NIVEL DA ESTACAO"),
        "pressao_min_mb": _coluna(df, "PRESS", "MIN. NA HORA"),
        "temp_max_c": _coluna(df, "TEMPERATURA M", "XIMA NA HORA"),
        "umid_min_pct": _coluna(df, "UMIDADE REL. MIN"),
        "rajada_ms": _coluna(df, "RAJADA"),
        "vento_ms": _coluna(df, "VENTO, VELOCIDADE"),
    }
    hora = df[col_hora].str.replace(" UTC", "", regex=False).str.replace(":", "", regex=False).str.zfill(4)
    data = df[col_data].str.replace("/", "-", regex=False)
    utc = pd.to_datetime(data + " " + hora, format="%Y-%m-%d %H%M")
    out = pd.DataFrame({"hora_local": utc - pd.Timedelta(hours=3)})  # São Paulo, UTC-3 (sem horário de verão desde 2019)
    for novo, orig in mapa.items():
        v = pd.to_numeric(df[orig].str.replace(",", ".", regex=False), errors="coerce")
        out[novo] = v.mask(v <= -9999)  # -9999 é nulo no INMET
    return out


def processar_inmet() -> pd.DataFrame:
    print(f"INMET: estação {ESTACAO}, dados horários convertidos para a hora local e agregados por dia")
    horario = pd.concat([ler_inmet_ano(a) for a in ANOS], ignore_index=True)
    # Os arquivos anuais estão em UTC; as primeiras 3h de 1º/jan caem no ano anterior.
    horario = horario[horario["hora_local"].dt.year.between(ANOS[0], ANOS[-1])].sort_values("hora_local")
    horario = horario.set_index("hora_local")
    # Grade horária completa: hora que falta no arquivo vira linha vazia, assim shift(3) é sempre 3 horas.
    horario = horario[~horario.index.duplicated()].asfreq("h")

    # Maior queda de pressão em 3 horas dentro do dia: sinal clássico de frente fria e temporal.
    horario["queda_3h"] = horario["pressao_mb"].shift(3) - horario["pressao_mb"]

    g = horario.groupby(horario.index.normalize())
    diario = pd.DataFrame(
        {
            "rajada_max_ms": g["rajada_ms"].max(),
            "vento_max_ms": g["vento_ms"].max(),
            "chuva_mm": g["chuva_mm"].sum(min_count=1),
            "pressao_min_mb": g["pressao_min_mb"].min(),
            "queda_pressao_mb": g["queda_3h"].max(),
            "temp_max_c": g["temp_max_c"].max(),
            "umid_min_pct": g["umid_min_pct"].min(),
            "horas_com_dado": g["rajada_ms"].count(),
        }
    )
    diario.index.name = "data"
    idx = pd.date_range(f"{ANOS[0]}-01-01", f"{ANOS[-1]}-12-31", freq="D", name="data")
    diario = diario.reindex(idx)
    diario["horas_com_dado"] = diario["horas_com_dado"].fillna(0).astype(int)
    PROC.mkdir(parents=True, exist_ok=True)
    diario.round(2).to_csv(PROC / "inmet_diario.csv")
    print(f"  salvo em dados/processados/inmet_diario.csv ({len(diario)} dias, {diario['rajada_max_ms'].isna().sum()} sem rajada)")
    return diario


def juntar() -> pd.DataFrame:
    aneel = pd.read_csv(PROC / "aneel_diario.csv", parse_dates=["data"], index_col="data")
    inmet = pd.read_csv(PROC / "inmet_diario.csv", parse_dates=["data"], index_col="data")
    diario = aneel.join(inmet, how="inner")

    # Falha do anemômetro da A701: de 29/03 a 01/09/2021 o vento médio fica em 0,0 o dia inteiro e a
    # rajada entre 0 e 1 m/s (fora desse período a menor rajada diária da série é 1,2 m/s). O INMET
    # gravou zero em vez de -9999, então é sensor parado, não calmaria. Vento e rajada viram nulos e
    # o dia fica marcado; o notebook tira esses dias do treino.
    periodo = (diario.index >= "2021-03-29") & (diario.index <= "2021-09-01")
    falha = periodo & (diario["vento_max_ms"] == 0)
    diario["falha_anemometro"] = falha.astype(int)
    diario.loc[falha, ["rajada_max_ms", "vento_max_ms"]] = np.nan
    print(f"  falha do anemômetro: {falha.sum()} dias com vento e rajada anulados")

    diario.round(2).to_csv(PROC / "diario.csv")
    print(f"diario.csv: {len(diario)} dias, {diario.shape[1]} colunas")
    return diario


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--so", choices=["aneel", "inmet"])
    args = p.parse_args()
    if args.so in (None, "aneel"):
        processar_aneel()
    if args.so in (None, "inmet"):
        processar_inmet()
    if args.so is None:
        juntar()
    return 0


if __name__ == "__main__":
    sys.exit(main())
