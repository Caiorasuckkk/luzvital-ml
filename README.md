# Luz Vital · Machine Learning

Global Solution CitizenTech · FIAP 2026.2 · IA & Machine Learning

Este repositório é só a parte de ML da Luz Vital. O projeto completo (API em C#, Cybersecurity e as demais
partes) está em **https://github.com/Caiorasuckkk/luzvital**.

## Ficha da CitizenTech

| Campo | Conteúdo |
| --- | --- |
| Nome | Luz Vital |
| Cidade e bairro | São Paulo, área de concessão da Enel SP |
| Cidadão beneficiado | Quem depende de energia em casa (oxigênio domiciliar, insulina na geladeira, cadeira motorizada, idoso acamado) e quem cuida dessas pessoas |
| Problema, em uma frase | Quando um temporal derruba a energia, quem depende dela para viver não é avisado antes, não sabe quanto tempo vai ficar sem luz nem onde achar uma tomada, e ninguém vai checar se está bem |
| Como funciona | Um modelo treinado com dados do INMET e da ANEEL prevê os dias de risco de apagão. O app avisa os cadastrados com antecedência, aciona vizinhos voluntários para checar essas pessoas e mostra pontos com energia por perto |
| O que este repositório faz | Treina o modelo que dá a probabilidade de um dia ser de apagão em massa e envia a previsão para a API (`POST /api/previsoes`) |
| Link do repositório principal | https://github.com/Caiorasuckkk/luzvital |
| Indicador de impacto | % de cadastrados avisados pelo menos 12h antes de um dia de risco · tempo até o primeiro check-in depois que a luz cai |
| ODS conectados | 3, 7, 10, 11 e 13 |

## Integrantes

- Caio Rasuck RM 93645
- Arthur Albuquerque RM 93025

## Resultado

XGBoost (`xgb-v1`) treinado de 2019 a 2023 e testado em 2024 e 2025, com limiar 0,125, escolhido para
privilegiar o recall:

| Recall | Precisão | F1 | PR-AUC | Apagões avisados no teste |
| --- | --- | --- | --- | --- |
| 0,622 | 0,272 | 0,378 | 0,314 | 28 de 45 (os 5 maiores, todos) |

Discussão completa em [RELATORIO_ML.md](RELATORIO_ML.md) e no notebook [luzvital_ml.ipynb](luzvital_ml.ipynb).

## Arquivos

| Arquivo | O que é |
| --- | --- |
| `luzvital_ml.ipynb` | o notebook, executado, com todas as saídas |
| `RELATORIO_ML.md` | relatório de 2 a 4 páginas |
| `baixar_dados.py` | baixa as bases da ANEEL e do INMET para `dados/brutos/` (fora do git) |
| `preparar_dados.py` | lê os brutos e gera `dados/processados/diario.csv` |
| `luzvital.py` | atributos e conversão para as faixas da API, usados pelo notebook e pelo envio |
| `enviar_previsao.py` | gera a previsão para uma data e manda para a API |
| `dados/README.md` | fonte, link, data do download e colunas de cada base |
| `dados/processados/` | tabelas diárias (no git) |
| `modelo/` | modelo treinado (`modelo_luzvital.joblib`) e `metadados.json` |
| `ROTEIRO_VIDEO.md` | roteiro do vídeo de 5 minutos |
| `prompts.md` | registro do uso de IA |

## Como rodar

Python 3.12 ou mais novo.

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows (no Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
```

**Só o notebook** (a tabela diária já está no git, não precisa baixar nada):

```bash
jupyter notebook luzvital_ml.ipynb
# ou, para executar do começo ao fim sem abrir:
python -m nbconvert --to notebook --execute --inplace luzvital_ml.ipynb
```

**Refazer tudo a partir das bases públicas** (~2,3 GB de download):

```bash
python baixar_dados.py     # ANEEL baixa sozinho; o INMET pode recusar cliente automático (veja dados/README.md)
python preparar_dados.py   # leva alguns minutos: lê ~17 GB de CSV da ANEEL em pedaços
```

**Enviar uma previsão para a API** (a API do repositório principal roda em `http://localhost:5131`):

```bash
python enviar_previsao.py --data 2026-11-20 --rajada 19 --vento 6 --chuva 25 --pressao-min 917 \
    --queda-pressao 2.5 --temp-max 31 --umid-min 45 --chuva-3d 10
python enviar_previsao.py --exemplo temporal --nao-enviar   # só imprime o JSON
```

Se a API estiver fora do ar, o script imprime o JSON e avisa que nada foi enviado.

**O que vai no campo `probabilidade`.** O script envia um **score de risco (0 a 1)**, não a probabilidade do
modelo. Uma conversão linear por partes leva o limiar de alerta do modelo (0,125) para 0,4 e o limiar alto
(0,461) para 0,7, que são os cortes de Atenção e Alto da API, e estica em linha reta o que fica entre eles.
Um score de 0,82 quer dizer que o dia está na faixa Alto, **não** que há 82% de chance de apagão. O campo
continua se chamando `probabilidade` porque é o contrato da API.

Dados: as bases são públicas (ANEEL e INMET) e reais; nada no modelo é simulado.
