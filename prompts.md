# Uso de IA no projeto

A GS permite IA como copiloto, desde que os prompts fiquem registrados e a gente saiba explicar cada linha. Cada entrada: data, quem usou, ferramenta, o que foi pedido e o que foi aproveitado.

## 05/11/2026 · Caio · Claude

- **Pedido:** análise do PDF da GS, escolha do problema (apagões da Enel em SP), pesquisa de recorrência dos apagões e das bases públicas (INMET, ANEEL), divisão de entregas por disciplina.
- **Aproveitado:** a ideia da Luz Vital, o plano por disciplina e as fontes que conferimos. (Entrada copiada do repositório principal, porque a escolha das bases veio daqui.)

## 07/11/2026 · Caio · Claude Code

- **Pedido:** entrega de IA & ML neste repositório: download reproduzível das bases da ANEEL (2019 a 2025) e do INMET (A701), leitura em pedaços filtrando a Enel SP e as interrupções não programadas, tabela diária, rótulo de dia de apagão, comparação de regressão logística, Random Forest e XGBoost com 10+ combinações de hiperparâmetros e validação cruzada só no treino, limiar pensando no cidadão, importância das variáveis, notebook executado, relatório, script de envio para a API e material do vídeo.
- **Decisões nossas no caminho:**
  - Rótulo: o percentil 97 calculado só no treino (316.591 UCs) foi aprovado depois de ver as colunas, a contagem de dias e a confirmação de que os três apagões conhecidos são positivos.
  - A premissa de usar o clima do dia como previsão da véspera ficou escrita como limitação, com um modelo de comparação que só usa dados da véspera.
  - Anemômetro da A701 parado em 2021 (vento zerado, gravado como zero e não como nulo): aprovamos anular vento e rajada desses dias e tirá-los do treino, em vez de imputar.
  - Pedimos uma análise de sensibilidade com rótulo relativo (4x a mediana de 90 dias) por causa do aumento das interrupções, sem trocar o modelo principal.
  - A queda de pressão ficou no modelo como especificada, com a explicação da maré atmosférica no relatório.
- **O que a IA não conseguiu fazer:** o portal do INMET derruba conexões de clientes automáticos. Os 7 ZIPs foram baixados por nós no navegador e colocados em `dados/brutos/inmet/`.
- **Aproveitado:** os scripts de download e preparo, o notebook, o modelo, o `enviar_previsao.py`, o relatório e o roteiro do vídeo. Conferimos as colunas reais contra o dicionário da ANEEL e o cabeçalho do INMET antes de modelar.
