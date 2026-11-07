# Dados

Todas as bases são públicas e reais. Nada aqui é simulado.

| Pasta | O que tem | No git? |
| --- | --- | --- |
| `brutos/aneel/` | 7 ZIPs anuais da ANEEL (2019 a 2025, ~1,6 GB) e os 2 dicionários de dados em PDF | não, baixe com `python baixar_dados.py` |
| `brutos/inmet/` | 7 ZIPs anuais do INMET (2019 a 2025, ~700 MB) com todas as estações automáticas | não |
| `processados/aneel_diario.csv` | interrupções da Enel SP por dia | sim |
| `processados/inmet_diario.csv` | clima da estação A701 por dia, como veio do INMET | sim |
| `processados/diario.csv` | as duas juntas, com a falha do anemômetro tratada; é a tabela que o notebook usa | sim |

Os processados são gerados por `python preparar_dados.py`.

## 1. ANEEL: Interrupções de Energia Elétrica nas Redes de Distribuição

- **Fonte:** Agência Nacional de Energia Elétrica (ANEEL), Portal de Dados Abertos.
- **Página:** https://dadosabertos.aneel.gov.br/dataset/interrupcoes-de-energia-eletrica-nas-redes-de-distribuicao
- **Arquivos:** `interrupcoes-energia-eletrica-2019.zip` a `interrupcoes-energia-eletrica-2025.zip` (um CSV
  nacional por ano, `;`, UTF-8, cerca de 2,4 GB descompactado por ano). Os endereços exatos estão em
  `baixar_dados.py`, tirados da API do catálogo (CKAN).
- **Data do download:** 07/11/2026. Na página, os arquivos de 2019 a 2025 constam como atualizados em
  04/08/2026 (o campo `DatGeracaoConjuntoDados` dos arquivos diz 24/07/2026).
- **Dicionário de dados:** usamos o "Dicionário de dados (dados até dez/2025)", versão 1.0 de 11/10/2022,
  que vale para os anos usados. O dicionário "a partir de jan/2026" renomeia os campos
  (`QtdConsumidoresAfetados`, `NomAgente` etc.) e não se aplica a 2019–2025. Os nomes abaixo foram
  conferidos no cabeçalho real dos arquivos.

**Colunas usadas**

| Coluna | Uso |
| --- | --- |
| `NumCPFCNPJ` | filtro da distribuidora: `61695227000193`, Eletropaulo Metropolitana Eletricidade de São Paulo S.A. (Enel SP) |
| `SigAgente`, `NomAgenteRegulado` | conferência: em todos os anos a sigla é `ELETROPAULO` (nunca "ENEL SP") |
| `DscTipoInterrupcao` | só `Não Programada` |
| `DatInicioInterrupcao` | dia da interrupção (o dia em que ela começou) |
| `NumUnidadeConsumidora` | número de unidades consumidoras atingidas; somado por dia |
| `IdeMotivoInterrupcao` | contado à parte quando `6` (expurgo por dia crítico); não entra no modelo |

O dicionário chama a última coluna de `IdeMotivoExpurgo`; no arquivo ela aparece como
`IdeMotivoInterrupcao`, com os mesmos códigos.

**Leitura:** em pedaços de 2 milhões de linhas e só com as colunas acima (`preparar_dados.py`), porque os
arquivos são nacionais. A Enel SP tem de 237 mil (2020) a 474 mil (2025) registros por ano, dos quais de
225 mil a 463 mil são não programados.

**`aneel_diario.csv`:** `data`, `ucs_atingidas` (soma de `NumUnidadeConsumidora` das interrupções não
programadas que começaram no dia), `n_interrupcoes`, `ucs_expurgo_dia_critico`. São 2.557 dias, de
01/01/2019 a 31/12/2025, sem nenhum dia faltando.

## 2. INMET: dados históricos da estação automática A701

- **Fonte:** Instituto Nacional de Meteorologia (INMET), Banco de Dados Meteorológicos.
- **Página:** https://portal.inmet.gov.br/dadoshistoricos
- **Arquivos:** `2019.zip` a `2025.zip` (`https://portal.inmet.gov.br/uploads/dadoshistoricos/<ano>.zip`),
  um ZIP por ano com o CSV horário de todas as estações automáticas. Usamos só
  `INMET_SE_SP_A701_SAO PAULO - MIRANTE_01-01-<ano>_A_31-12-<ano>.CSV`.
- **Estação:** A701, São Paulo – Mirante de Santana, latitude −23,496, longitude −46,620, altitude 785,64 m.
- **Data do download:** 07/11/2026, pelo navegador. O portal do INMET recusa conexões de clientes
  automáticos (a conexão é derrubada até na página inicial), então `baixar_dados.py` tenta e, se falhar,
  explica onde salvar os arquivos baixados à mão.
- **Formato:** 8 linhas de cabeçalho da estação, depois `;`, latin-1, decimal com vírgula, data
  `AAAA/MM/DD` e hora `HHMM UTC`. `-9999` é nulo. Mesmos nomes de coluna nos 7 anos.

**Colunas usadas e agregação por dia**

| Atributo diário | Coluna do INMET | Agregação |
| --- | --- | --- |
| `rajada_max_ms` | `VENTO, RAJADA MAXIMA (m/s)` | máximo |
| `vento_max_ms` | `VENTO, VELOCIDADE HORARIA (m/s)` | máximo |
| `chuva_mm` | `PRECIPITAÇÃO TOTAL, HORÁRIO (mm)` | soma (nulo se nenhuma hora tiver dado) |
| `pressao_min_mb` | `PRESSÃO ATMOSFERICA MIN. NA HORA ANT. (AUT) (mB)` | mínimo |
| `queda_pressao_mb` | `PRESSAO ATMOSFERICA AO NIVEL DA ESTACAO, HORARIA (mB)` | maior queda em 3 horas dentro do dia |
| `temp_max_c` | `TEMPERATURA MÁXIMA NA HORA ANT. (AUT) (°C)` | máximo |
| `umid_min_pct` | `UMIDADE REL. MIN. NA HORA ANT. (AUT) (%)` | mínimo |
| `horas_com_dado` | (conta de horas com rajada) | controle de qualidade |

As horas são convertidas de UTC para o horário de São Paulo (UTC−3, sem horário de verão desde 2019) antes
de agregar, para o dia bater com o da ANEEL. A queda em 3 h é calculada numa grade horária completa (hora
faltante vira vazio), então é sempre um intervalo de 3 horas.

## Problemas de qualidade encontrados e o que foi feito

| Problema | Dias | Tratamento |
| --- | --- | --- |
| Anemômetro parado: vento médio 0,0 o dia inteiro e rajada de 0 a 1,6 m/s, entre 29/03 e 01/09/2021 (fora disso, a menor rajada diária é 3,5 m/s). O INMET gravou zero em vez de -9999. | 106 (2 dias de apagão: 02/05 e 28/08/2021) | vento e rajada viram nulos em `diario.csv` (coluna `falha_anemometro`); esses dias saem do treino |
| Pluviômetro sem dado: 25/08 a 11/09/2023 e 27/11/2023 | 17 (nenhum dia de apagão) | chuva nula, imputada pela mediana do treino (0 mm) no pipeline |
| Menos de 18 h de dado no dia | 15 (nenhum dia de apagão) | mantidos; máximo e soma do dia podem estar subestimados |

Detalhes e gráficos na seção 3 do notebook.

## Rótulo

`apagao = 1` quando `ucs_atingidas` passa de **316.591**, o percentil 97 do período de treino (2019 a 2023).
São 100 dias: 55 no treino (3,0%) e 45 no teste (6,2%). Os três grandes apagões recentes (03/11/2023,
11/10/2024 e 10/12/2025) são os três maiores valores da série.
