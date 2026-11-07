"""Atributos e score da API, num lugar só para o notebook e o enviar_previsao.py montarem tudo igual."""

from __future__ import annotations

import numpy as np
import pandas as pd

# Clima do dia, agregado da estação A701 (ver preparar_dados.py)
CLIMA = [
    "rajada_max_ms",
    "vento_max_ms",
    "chuva_mm",
    "pressao_min_mb",
    "queda_pressao_mb",
    "temp_max_c",
    "umid_min_pct",
]


def _mes(indice: pd.DatetimeIndex) -> pd.DataFrame:
    # Mês em seno/cosseno: dezembro fica perto de janeiro, o que um número de 1 a 12 não diz.
    angulo = 2 * np.pi * indice.month / 12
    return pd.DataFrame({"mes_sin": np.sin(angulo), "mes_cos": np.cos(angulo)}, index=indice)


def _chuva_3d_anteriores(chuva: pd.Series) -> pd.Series:
    # Soma de D-1, D-2 e D-3 (solo encharcado e árvores mais fáceis de cair)
    return chuva.shift(1).rolling(3, min_periods=1).sum()


def montar_atributos(df: pd.DataFrame) -> pd.DataFrame:
    """Modelo principal: clima do próprio dia + mês + chuva dos 3 dias anteriores.

    Premissa: em produção, o "clima do dia" é a previsão meteorológica feita na véspera.
    """
    X = df[CLIMA].copy()
    X["chuva_3d_ant"] = _chuva_3d_anteriores(df["chuva_mm"])
    return X.join(_mes(df.index))


def montar_atributos_vespera(df: pd.DataFrame) -> pd.DataFrame:
    """Comparação: só o que já foi observado até a véspera (clima de D-1 e defasagens)."""
    X = pd.DataFrame(index=df.index)
    for c in CLIMA:
        X[f"{c}_d1"] = df[c].shift(1)
    X["rajada_max_ms_d2"] = df["rajada_max_ms"].shift(2)
    X["chuva_3d_ant"] = _chuva_3d_anteriores(df["chuva_mm"])
    return X.join(_mes(df.index))


def para_probabilidade_api(p: float, limiar: float, limiar_alto: float) -> float:
    """Converte a probabilidade do modelo no score de risco da API: o limiar vira 0,4 e o limiar alto vira 0,7.

    É um score, não uma probabilidade: 0,82 não significa 82% de chance de apagão.
    """
    p = float(min(max(p, 0.0), 1.0))
    if p < limiar:
        return 0.4 * p / limiar
    if p < limiar_alto:
        return 0.4 + 0.3 * (p - limiar) / (limiar_alto - limiar)
    return min(0.7 + 0.3 * (p - limiar_alto) / (1 - limiar_alto), 1.0)
