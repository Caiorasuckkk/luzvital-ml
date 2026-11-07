# Roteiro do vídeo (até 5 min)

O roteiro segue os critérios da disciplina, na ordem. O tempo de cada bloco é uma sugestão. O que mostrar na
tela está entre colchetes, e o resto é a fala.

## 0:00 – 0:30 · Problema

[Tela: título do notebook]

Quando um temporal derruba a energia em São Paulo, quem tem concentrador de oxigênio ou insulina na geladeira
não é avisado antes. Em 10 de dezembro de 2025 foram 4,2 milhões de unidades consumidoras sem luz num dia só.
A Luz Vital avisa essas pessoas e aciona vizinhos voluntários. O modelo que mostro agora diz, para cada dia, a
probabilidade de ser um dia de apagão em massa na área da Enel SP.

## 0:30 – 1:15 · Dados reais

[Tela: `dados/README.md` e o gráfico de UCs por dia, seção 2]

Duas bases públicas, de 2019 a 2025. Da ANEEL, as interrupções de energia: um arquivo nacional de 2,4 GB por
ano, que a gente lê em pedaços e filtra pelo CNPJ da Enel SP e por interrupção não programada. Do INMET, a
estação automática do Mirante de Santana, hora a hora. Dia de apagão é o dia com mais de 316 mil unidades
atingidas, o percentil 97 do treino. Os três grandes apagões recentes são os três maiores dias da série.

## 1:15 – 2:00 · Preparo e divisão

[Tela: gráfico da rajada com 2021 destacado, seção 3.1]

Achamos um problema nos dados: em 2021 o anemômetro da estação ficou parado por 106 dias e o INMET gravou zero
em vez de nulo. Dois apagões caem nesse período. Se a gente deixasse, o modelo aprenderia que dá apagão sem
vento. Esses dias viraram nulos e saíram do treino.

[Tela: tabela de divisão, seção 4]

A divisão é por tempo, sem embaralhar: treino até 2023, teste em 2024 e 2025. O teste fica guardado até o fim.

## 2:00 – 2:50 · Treino com parâmetros diferentes

[Tela: tabela de comparação e a tabela das 24 combinações do XGBoost, seções 5 e 6]

Comparamos regressão logística, Random Forest e XGBoost, com 20, 36 e 24 combinações de hiperparâmetros, todas
com validação cruzada temporal só no treino. Dá para ver o overfitting na tabela: as árvores mais profundas
chegam a 1,0 no treino e pioram na validação. Venceu o XGBoost mais simples da grade.

## 2:50 – 3:50 · Resultados e escolha do limiar

[Tela: gráfico treino × validação × teste, seção 8.1, depois a curva precisão × recall, seção 7]

No treino o XGBoost acerta mais de 90% dos apagões; no teste, 62%. É overfitting, mas a validação cruzada já
mostrava esse nível. Para escolher o limiar, a pergunta foi: o que é pior para quem depende de energia? Alarme
falso custa pouco, e apagão sem aviso pode custar uma vida. Por isso o limiar maximiza o F2, que dá o dobro do
peso ao recall.

[Tela: matriz de confusão e a tabela dos 45 dias, seção 8.2]

No teste, o modelo avisou 28 dos 45 dias de apagão, incluindo os 5 com mais de 1 milhão de casas sem luz.
Precisão de 27%: um alerta por semana, e 1 em cada 4 vira apagão em massa. Os alarmes falsos não são dias
calmos, têm o dobro de interrupções de um dia comum.

## 3:50 – 4:20 · Importância e limitação

[Tela: importância por permutação, seção 8.3, e a tabela da véspera, seção 9]

Rajada e chuva do dia carregam quase todo o modelo. A principal limitação é essa: o modelo usa o clima do dia
como se fosse a previsão do tempo. Só com o que se sabe na véspera, para pegar os mesmos apagões seriam 126
alertas por ano em vez de 52. Em produção, quem alimenta o modelo é a previsão meteorológica.

## 4:20 – 5:00 · Integração e conclusão para o cidadão

[Tela: terminal rodando `python enviar_previsao.py --exemplo temporal` com a API ligada e a resposta com nível
Alto e o alerta aberto]

A previsão vai direto para a API da Luz Vital. Convertemos a probabilidade para que o limiar do modelo vire o
0,4 da API, que abre o alerta. Para o cidadão: em 2024 e 2025, 28 dos 45 apagões em massa teriam sido avisados
com antecedência, tempo para carregar a bateria e combinar com um vizinho. Mas 17 passaram sem aviso, então
o alerta não substitui o plano da família, e o check-in dos voluntários depois que a luz cai continua sendo
necessário.
