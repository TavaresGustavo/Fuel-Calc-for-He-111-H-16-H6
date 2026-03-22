# 🛩️ IL-2 Sturmovik: He-111 Tactical Flight Planner

Uma aplicação web desenvolvida em Python (Streamlit) para atuar como um painel de "segunda tela" ou "kneeboard" eletrônico para pilotos virtuais de **IL-2 Sturmovik: Great Battles**. 

A ferramenta é focada na engenharia de voo dos bombardeiros **Heinkel He-111 (versões H-6 e H-16)**, automatizando os cálculos complexos de peso máximo de decolagem, arrasto de payload e consumo de combustível.

## 🚀 Funcionalidades

* **Cálculo Estrutural (Weight & Balance):** Valida em tempo real se a combinação de combustível, modificações de armamento e bombas excede o limite máximo estrutural da aeronave.
* **Sincronia de Hangar:** Contém os exatos mesmos presets de bombas (Payloads) oficiais do jogo, com os pesos balísticos reais corrigidos (ex: SC 1000 = 1090 kg).
* **Gestão de Combustível:** Calcula o tempo de rota e os litros exatos necessários, permitindo adicionar uma margem de segurança configurável (reserva de combate).
* **Integração JSON:** Permite importar arquivos `.json` exportados do [IL-2 Mission Planner Revived](https://serverror.github.io/IL2-Mission-Planner/). A aplicação lê as coordenadas dos waypoints, extrai a velocidade programada e calcula a distância euclidiana total automaticamente.
* **Dark Mode Nativo:** Interface escurecida projetada para não cansar a visão do piloto em simulações de voo noturno ou em ambientes com pouca luz.

## 🛠️ Tecnologias Utilizadas
* **Python 3**
* **Streamlit** (Framework de interface e web server)
* **JSON / Math** (Processamento de dados de rota)

## 🎮 Como Usar

A aplicação está hospedada na nuvem e não requer nenhuma instalação. Acesse a calculadora pelo navegador do seu PC, tablet ou celular:

👉 **https://fuelcalc111.streamlit.app/**

**Fluxo sugerido de planejamento:**
1. Abra o [IL-2 Mission Planner](https://serverror.github.io/IL2-Mission-Planner/) e desenhe sua rota até o alvo.
2. Exporte o plano de voo clicando em "Export JSON".
3. Arraste o arquivo `.json` para dentro desta calculadora.
4. Selecione a variante do seu He-111 e escolha o armamento.
5. Ajuste a margem de combustível e configure seu avião no hangar do jogo com a porcentagem indicada no painel verde!

---
*Desenvolvido para a comunidade de simulação de voo do IL-2 Sturmovik.*
