"""Gera a previsão de risco de apagão para uma data e envia para a API da Luz Vital.

Entrada: a previsão do tempo para o dia (rajada, vento, chuva, pressão, temperatura, umidade) e a chuva
observada nos 3 dias anteriores. Saída: o JSON do contrato da API

    POST http://localhost:5131/api/previsoes
    { "data": "2026-11-20", "probabilidade": 0.82, "versaoModelo": "xgb-v1" }

O valor enviado no campo "probabilidade" NÃO é a probabilidade do modelo: é um score de risco (0 a 1)
na escala das faixas da API. A probabilidade do modelo passa por uma conversão linear por partes
(para_probabilidade_api em luzvital.py): o limiar de alerta 0,125 vira 0,4 (Atenção) e o limiar alto
0,461 vira 0,7 (Alto), e o que fica entre eles é esticado em linha reta. A ordem entre os dias não muda,
mas um score de 0,82 não quer dizer 82% de chance de apagão; quer dizer que o dia está na faixa Alto.
O campo continua se chamando "probabilidade" porque esse é o contrato da API.

Se a API estiver fora do ar, o script só imprime o JSON.

Exemplos:
    python enviar_previsao.py --data 2026-11-20 --rajada 19 --vento 6 --chuva 25 --pressao-min 917 \
        --queda-pressao 2.5 --temp-max 31 --umid-min 45 --chuva-3d 10
    python enviar_previsao.py --exemplo temporal --nao-enviar
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, timedelta
from pathlib import Path

import joblib
import pandas as pd
import requests

from luzvital import montar_atributos, para_probabilidade_api

RAIZ = Path(__file__).resolve().parent
MODELO = RAIZ / "modelo" / "modelo_luzvital.joblib"
URL_PADRAO = "http://localhost:5131/api/previsoes"

EXEMPLOS = {
    # parecido com 10/12/2025: ventania forte, chuva moderada, pressão muito baixa
    "temporal": dict(rajada=21.0, vento=8.0, chuva=18.0, pressao_min=914.0, queda_pressao=2.4, temp_max=28.0, umid_min=40.0, chuva_3d=5.0),
    # dia comum de primavera, sem chuva
    "calmo": dict(rajada=8.5, vento=3.4, chuva=0.0, pressao_min=925.0, queda_pressao=2.2, temp_max=27.0, umid_min=40.0, chuva_3d=0.0),
}


def prever(pacote: dict, dia: date, clima: dict) -> dict:
    # Monta a mesma tabela que o notebook usa, com 4 dias: os 3 anteriores só servem para a chuva acumulada.
    indice = pd.date_range(pd.Timestamp(dia) - pd.Timedelta(days=3), periods=4, freq="D")
    df = pd.DataFrame(index=indice, columns=["rajada_max_ms", "vento_max_ms", "chuva_mm", "pressao_min_mb",
                                             "queda_pressao_mb", "temp_max_c", "umid_min_pct"], dtype=float)
    df.loc[indice[:3], "chuva_mm"] = clima["chuva_3d"] / 3
    df.loc[indice[-1]] = [clima["rajada"], clima["vento"], clima["chuva"], clima["pressao_min"],
                          clima["queda_pressao"], clima["temp_max"], clima["umid_min"]]
    X = montar_atributos(df).loc[[indice[-1]], pacote["atributos"]]

    p_modelo = float(pacote["modelo"].predict_proba(X)[:, 1][0])
    score = para_probabilidade_api(p_modelo, pacote["limiar"], pacote["limiar_alto"])
    nivel = "Alto" if score >= 0.7 else ("Atencao" if score >= 0.4 else "Baixo")
    # o campo do contrato se chama "probabilidade", mas o valor é o score de risco (0 a 1)
    return {"corpo": {"data": dia.isoformat(), "probabilidade": round(score, 3), "versaoModelo": pacote["versao"]},
            "probabilidade_modelo": round(p_modelo, 4), "score_risco": round(score, 3), "nivel_esperado": nivel}


def enviar(url: str, corpo: dict) -> None:
    try:
        r = requests.post(url, json=corpo, timeout=10)
    except requests.RequestException as e:
        print(f"\nAPI fora do ar ({url}): {e.__class__.__name__}. Nada foi enviado; o JSON está acima.")
        return
    print(f"\nPOST {url}: HTTP {r.status_code}")
    print(r.text[:1000])


def main() -> int:
    p = argparse.ArgumentParser(description="Previsão de dia de apagão para a API da Luz Vital",
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("--data", type=date.fromisoformat, default=date.today() + timedelta(days=1),
                   help="dia previsto, AAAA-MM-DD (padrão: amanhã; a API recusa data passada)")
    p.add_argument("--exemplo", choices=EXEMPLOS, help="usa valores de exemplo em vez de informar o clima")
    p.add_argument("--rajada", type=float, help="rajada máxima prevista (m/s)")
    p.add_argument("--vento", type=float, help="vento máximo previsto (m/s)")
    p.add_argument("--chuva", type=float, help="chuva total prevista (mm)")
    p.add_argument("--pressao-min", type=float, help="pressão mínima prevista no nível da estação (mB)")
    p.add_argument("--queda-pressao", type=float, help="maior queda de pressão em 3 h (mB)")
    p.add_argument("--temp-max", type=float, help="temperatura máxima prevista (°C)")
    p.add_argument("--umid-min", type=float, help="umidade relativa mínima prevista (%%)")
    p.add_argument("--chuva-3d", type=float, default=0.0, help="chuva observada nos 3 dias anteriores, somada (mm)")
    p.add_argument("--url", default=URL_PADRAO)
    p.add_argument("--nao-enviar", action="store_true", help="só imprime o JSON")
    a = p.parse_args()

    if a.exemplo:
        clima = EXEMPLOS[a.exemplo]
    else:
        clima = dict(rajada=a.rajada, vento=a.vento, chuva=a.chuva, pressao_min=a.pressao_min,
                     queda_pressao=a.queda_pressao, temp_max=a.temp_max, umid_min=a.umid_min, chuva_3d=a.chuva_3d)
        faltando = [k for k, v in clima.items() if v is None]
        if faltando:
            # O modelo imputa nulos com a mediana do treino, mas uma previsão sem rajada ou chuva não vale nada.
            p.error(f"informe o clima previsto ou use --exemplo. Faltando: {', '.join(faltando)}")

    if not MODELO.exists():
        print(f"Modelo não encontrado em {MODELO}. Rode o notebook luzvital_ml.ipynb antes.")
        return 1
    pacote = joblib.load(MODELO)
    r = prever(pacote, a.data, clima)

    print(f"Modelo {pacote['versao']}, probabilidade do modelo {r['probabilidade_modelo']:.3f} "
          f"(limiar {pacote['limiar']:.3f}, alto {pacote['limiar_alto']:.3f})")
    print(f"Score de risco (0 a 1) enviado à API: {r['score_risco']:.3f}, nível esperado: {r['nivel_esperado']} "
          f"(o score não é chance de apagão; veja RELATORIO_ML.md, seção 5)")
    print(json.dumps(r["corpo"], ensure_ascii=False))
    if not a.nao_enviar:
        enviar(a.url, r["corpo"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
