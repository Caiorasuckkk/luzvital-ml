# Relatório de IA & Machine Learning · Luz Vital

Global Solution CitizenTech · FIAP 2026.2 · Caio Rasuck (RM 93645) e Arthur Albuquerque (RM 93025)
Notebook: `luzvital_ml.ipynb` · Repositório principal: https://github.com/Caiorasuckkk/luzvital

## 1. Problema e dados

Quando um temporal derruba a energia em São Paulo, quem depende dela em casa (oxigênio domiciliar,
insulina na geladeira, cadeira motorizada) não é avisado antes. O modelo responde a uma pergunta por dia:
**qual a probabilidade de amanhã ser um dia de apagão em massa na área da Enel SP?** A resposta vai para a
API da Luz Vital (`POST /api/previsoes`), que abre alerta a partir de 0,4 e avisa os cadastrados e os
voluntários do bairro.

Duas bases públicas, de 2019 a 2025 (detalhes em `dados/README.md`):

- **ANEEL**, *Interrupções de Energia Elétrica nas Redes de Distribuição*: um CSV nacional por ano (~2,4 GB
  cada), lido em pedaços e filtrado pelo CNPJ da Eletropaulo (Enel SP) e por interrupção **não programada**.
  Somamos as unidades consumidoras (UCs) atingidas pelas interrupções que começaram em cada dia.
- **INMET**, estação automática **A701** (Mirante de Santana), dados horários convertidos para o horário
  local e agregados por dia: rajada máxima, vento máximo, chuva total, pressão mínima, maior queda de
  pressão em 3 h, temperatura máxima e umidade mínima.

**Rótulo.** Dia de apagão é o dia com mais de **316.591 UCs atingidas**, o percentil 97 calculado só no
treino. Dá 100 dias em 2.557. Os três grandes apagões recentes (03/11/2023, 11/10/2024 e 10/12/2025) são os
três maiores valores da série, com 2,6, 3,1 e 4,2 milhões de UCs.

## 2. Preparo e divisão treino/teste

**Qualidade dos dados.** O anemômetro da A701 ficou parado em 106 dias entre 29/03 e 01/09/2021: vento
médio 0,0 o dia inteiro e rajada de 0 a 1,6 m/s, quando a menor rajada diária no resto da série é 3,5 m/s.
O INMET gravou zero em vez do código de nulo. Dois dias de apagão caem nesse período (02/05/2021, com 853
mil UCs, e 28/08/2021, com 810 mil). Vento e rajada desses dias viraram nulos e os dias saíram do treino:
com zero o modelo aprenderia "apagão sem vento", e com a mediana ganharia dois apagões com vento normal que
não existiram. Os 17 dias sem chuva registrada (falha do pluviômetro em 2023) e os 15 dias com menos de 18 h
de dado ficaram na base; nenhum deles é dia de apagão.

**Atributos.** Clima do dia (as 7 variáveis), mês em seno e cosseno e chuva acumulada dos 3 dias anteriores.
O código fica em `luzvital.py`, usado pelo notebook e pelo `enviar_previsao.py`.

**Divisão temporal, sem embaralhar.** Treino de 2019 a 2023 (1.720 dias, 53 de apagão, 3,1%) e teste em
2024 e 2025 (731 dias, 45 de apagão, 6,2%). As classes são desbalanceadas (31 dias normais para cada dia de
apagão), tratadas com `class_weight` na logística e no Random Forest e com `scale_pos_weight` no XGBoost.
Os nulos são imputados pela mediana do treino dentro do pipeline.

## 3. Treino com parâmetros diferentes

Validação cruzada **só no treino**, temporal (`TimeSeriesSplit`, 4 dobras: cada uma treina no passado e
valida no período seguinte). A métrica de escolha é a PR-AUC, que avalia o ranking da classe rara sem
depender de limiar.

| Modelo | Combinações | Hiperparâmetros variados | Melhor PR-AUC na validação |
| --- | --- | --- | --- |
| Regressão logística (base) | 20 | C, l1_ratio (L1/L2), class_weight | 0,342 ± 0,180 |
| Random Forest | 36 | n_estimators, max_depth, min_samples_leaf, max_features | 0,318 ± 0,176 |
| **XGBoost** | 24 | max_depth, learning_rate, n_estimators, scale_pos_weight | **0,355 ± 0,251** |

A tabela das 24 combinações do XGBoost está na seção 6 do notebook. As combinações com árvores mais
profundas, mais árvores ou taxa de aprendizado 0,1 chegam a PR-AUC 1,000 no treino da dobra e pioram na
validação. A melhor é a mais contida da grade: profundidade 2, 150 árvores, taxa 0,03 e `scale_pos_weight`
5,6, a raiz da proporção, em vez dos 31,5 da proporção cheia.

## 4. Resultados em treino e teste

Cada modelo com a sua melhor combinação e o seu limiar F2 (seção 5):

| Modelo | PR-AUC ajuste | PR-AUC validação | PR-AUC teste | Recall ajuste | Recall teste | Precisão teste | F1 teste |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Regressão logística | 0,401 | 0,326 | 0,404 | 0,623 | 0,467 | 0,356 | 0,404 |
| Random Forest | 0,673 | 0,325 | 0,314 | 0,925 | 0,422 | 0,345 | 0,380 |
| **XGBoost** | 0,616 | 0,351 | 0,314 | 0,906 | **0,622** | 0,272 | 0,378 |

Random Forest e XGBoost decoram o treino (PR-AUC de 0,62 a 0,67 e recall acima de 0,9 no ajuste) e caem no
teste para o nível que a validação cruzada já indicava. A distância entre ajuste e teste é overfitting, mas a
validação estimou bem o desempenho real. A logística quase não tem overfitting e teve a melhor PR-AUC no
teste.

## 5. Escolha do modelo e do limiar

**Modelo: XGBoost (`xgb-v1`).** Foi o melhor na validação cruzada, que é o critério definido antes de olhar o
teste. Os três praticamente empatam na validação (as diferenças são menores que o desvio entre dobras); no
limiar escolhido, o XGBoost avisa mais apagões: 28 dos 45 no teste, contra 21 da logística. A logística teve
PR-AUC de teste maior, e trocar de modelo depois de ver isso seria escolher pelo teste.

**Limiar pensando no cidadão.** Um alarme falso custa pouco (carregar a bateria, falar com um vizinho). Um
apagão sem aviso pode custar uma vida. Por isso o limiar maximiza o **F2**, que pesa o recall o dobro da
precisão, calculado nas probabilidades fora da dobra do treino: **0,125**. Um segundo limiar, o que maximiza
o F1, marca o risco Alto: **0,461**.

**Faixas da API.** A API abre alerta a partir de 0,4 (Atenção) e marca Alto a partir de 0,7. Em vez de mudar
a API, o `enviar_previsao.py` converte a probabilidade do modelo com uma função linear por partes que leva
0,125 para 0,4 e 0,461 para 0,7, sem mudar a ordem entre os dias. A regra da API passa a valer exatamente com
os limiares escolhidos. Testamos com a API rodando: um dia de temporal chegou como Alto e abriu alerta, e um
dia calmo chegou como Baixo, sem alerta.

**Teste (2024 e 2025), limiar 0,125:**

| Recall | Precisão | F1 | PR-AUC | Apagões avisados | Alarmes falsos |
| --- | --- | --- | --- | --- | --- |
| 0,622 | 0,272 | 0,378 | 0,314 (aleatório: 0,062) | 28 de 45 | 75 em 731 dias |

Matriz de confusão: 611 verdadeiros negativos, 75 falsos positivos, 17 falsos negativos e 28 verdadeiros
positivos. São cerca de 52 alertas por ano. Os 5 apagões com mais de 1 milhão de UCs foram todos avisados, e
8 dos 10 maiores. 11/10/2024 e 10/12/2025 chegariam à API como Alto (0,86 e 0,81). Na faixa Alto, 15 de 32
dias foram apagão; na faixa Atenção, 13 de 71.

Os 17 perdidos foram, na maioria, dias sem temporal no Mirante (rajada mediana de 9,2 m/s e chuva de 0,6
mm, contra 14,1 m/s e 12,3 mm nos avisados). As causas prováveis são temporal localizado longe da estação,
falha de rede sem relação com o clima e dias colados a outro apagão. Os alarmes falsos são dias de rede sob
estresse: mediana de 162 mil UCs atingidas, mais que o dobro de um dia típico do teste (73 mil).

## 6. Importância das variáveis

Na importância por permutação no teste, **rajada máxima** (queda de 0,12 na PR-AUC) e **chuva do dia**
(0,09) carregam quase todo o modelo. Vento médio pesa pouco e a chuva dos 3 dias anteriores quase nada.
Temperatura máxima e o cosseno do mês ficam negativos: o modelo aprendeu com eles uma relação de 2019–2023
que não se repetiu (2025 teve apagões em julho, agosto e setembro, fora da época de chuva).

**Por que a queda de pressão não separa os grupos.** A mediana da maior queda em 3 h é 2,2 mB tanto nos dias
de apagão quanto nos normais. Na faixa tropical a pressão sobe e desce duas vezes por dia por causa da maré
atmosférica (a maré barométrica semidiurna, provocada pelo aquecimento solar), com amplitude de 2 a 3 mB em
São Paulo, máxima perto das 10h e mínima no fim da tarde. A maior queda em 3 h quase sempre é essa descida
da tarde, que acontece todo dia. A queda de uma frente fria se dá ao longo de 12 a 24 h e se perde dentro do
ciclo diário.

## 7. Premissa, limitações e sensibilidade

**Premissa de antecedência.** O modelo usa o clima *observado* no dia como se fosse a *previsão* do tempo
feita na véspera. Em produção ele recebe a previsão meteorológica, que tem erro. Para medir o peso disso,
treinamos o mesmo XGBoost, com a mesma grade, só com o que se sabe na véspera (clima de D-1, rajada de D-2,
chuva dos 3 dias anteriores e mês):

| Versão | PR-AUC validação | PR-AUC teste | Recall teste | Precisão teste | Alertas por ano |
| --- | --- | --- | --- | --- | --- |
| Clima do dia (principal) | 0,355 | 0,314 | 0,622 | 0,272 | 52 |
| Só a véspera | 0,091 | 0,160 | 0,622 | 0,111 | 126 |

O clima de ontem diz pouco sobre o temporal de amanhã, porque o temporal de verão em São Paulo se forma em
poucas horas. Quase todo o valor do modelo vem de saber como estará o tempo no dia, então o desempenho real
fica entre as duas linhas, tão mais perto da primeira quanto melhor for a previsão de rajada e chuva. É a
principal limitação do trabalho.

**Outras limitações.** Uma estação só (Mirante de Santana) representa os 24 municípios da área da Enel SP. A
validação tem poucos positivos por dobra (5 a 20), por isso o desvio da PR-AUC é alto. O número de
interrupções cresce ao longo da série (mediana diária de 47 mil UCs em 2019 e 79 mil em 2025), e com limite
fixo o teste tem o dobro da proporção de dias de apagão do treino.

**Sensibilidade a esse crescimento.** Repetimos o modelo com um rótulo relativo: dia de apagão é o dia com
mais de 4 vezes a mediana das UCs atingidas nos 90 dias anteriores. Os dias de apagão ficam mais bem
distribuídos entre os anos (11 a 27 por ano) e a proporção do treino (5,5%) fica perto da do teste (6,4%). As
conclusões não mudam. O desempenho no teste é parecido (PR-AUC 0,38, recall 0,77, F1 0,40), rajada e chuva
continuam as duas variáveis mais importantes, e os dois rótulos concordam em 97% dos dias. O crescimento das
interrupções não explica o resultado do modelo principal.

**Próximos passos.** Alimentar o modelo com a previsão numérica do tempo (rajada e chuva previstas) e
retreinar com ela, usar mais estações da região metropolitana, testar grades mais simples para o XGBoost e
retreinar todo ano com os dados novos da ANEEL.

## 8. O que isso significa para o cidadão

Em 2024 e 2025, a Luz Vital teria avisado com antecedência **28 dos 45 dias de apagão em massa**, incluindo os
5 maiores, cada um com mais de 1 milhão de UCs sem luz. Para quem tem concentrador de oxigênio, esse aviso é
tempo para carregar a bateria, combinar com um vizinho e saber onde fica o ponto com energia mais próximo. O
custo é cerca de um alerta por semana, a maior parte sem apagão em massa; nos alertas Alto, metade se
confirmou. **17 apagões passaram sem aviso**, então o alerta não substitui o plano de cada família: quem
depende de energia precisa de bateria e do contato de um vizinho mesmo sem alerta, e o check-in dos
voluntários depois que a luz cai continua necessário.
