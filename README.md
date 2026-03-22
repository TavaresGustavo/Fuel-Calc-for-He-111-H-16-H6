# 🛩️ IL-2 Sturmovik: He-111 Tactical Planner & Bombsight Calculator

Uma aplicação web desenvolvida em Python (Streamlit) para atuar como um painel de "segunda tela" ou "kneeboard" eletrônico para pilotos virtuais de **IL-2 Sturmovik: Great Battles**. 

A ferramenta centraliza a engenharia de voo dos bombardeiros **Heinkel He-111 (versões H-6 e H-16)** e oferece uma calculadora balística para a mira Lotfe 7, automatizando cálculos complexos de peso, combustível e compensação de vento.



<img width="971" height="1454" alt="Screenshot 2026-03-22 130000" src="https://github.com/user-attachments/assets/0dafc48c-0e0c-42fc-80b7-65ecec51d91d" /><img width="956" height="891" alt="Screenshot 2026-03-22 130005" src="https://github.com/user-attachments/assets/a818eebe-9897-4142-b327-dd2478d5e2da" />



## 🚀 Funcionalidades Principais

A interface é dividida em dois painéis operacionais focados na rotina do piloto:

### 📊 Aba 1: Planejamento e Hangar
* **Cálculo Estrutural (Weight & Balance):** Valida em tempo real se a combinação de combustível, armamento fixo e bombas excede o limite máximo estrutural de decolagem.
* **Sincronia Oficial:** Contém exatamente os mesmos Presets de bombas do jogo, com os pesos balísticos reais corrigidos (ex: SC 1000 = 1090 kg).
* **Gestão Dinâmica de Combustível:** Calcula o tempo de rota e litros necessários, com um *slider* interativo para definir a margem de segurança de combate.
* **Integração JSON:** Permite importar arquivos `.json` do [IL-2 Mission Planner](https://serverror.github.io/IL2-Mission-Planner/). O sistema lê os waypoints, extrai a velocidade programada e calcula a distância euclidiana automaticamente.

### 🎯 Aba 2: Calculadora Balística (Mira Lotfe 7)
* **Conversão TAS:** Converte automaticamente a Velocidade Indicada (IAS) e Altitude para Velocidade Verdadeira (TAS).
* **Triângulo de Velocidades:** Utiliza trigonometria vetorial para cruzar a proa do avião com a velocidade e direção do vento.
* **Ajuste Fino de Mira:** Entrega a Velocidade no Solo (Ground Speed) exata e o Ângulo de Deriva (Drift) com indicação de esquerda/direita para inserção direta na mira Lotfe 7.

## 🛠️ Tecnologias Utilizadas
* **Python 3**
* **Streamlit** (Framework de interface UI/UX)
* **JSON & Math** (Processamento de rotas e vetores)
* **Dark Mode Nativo:** Interface escurecida projetada para imersão e conforto visual em voos noturnos.

## 🎮 Como Usar

A aplicação roda diretamente na nuvem, sem necessidade de instalação. Ideal para abrir no tablet ou celular ao lado do manche.

👉 **https://fuelcalc111.streamlit.app/**

**Fluxo sugerido de missão:**
1. Desenhe sua rota no [IL-2 Mission Planner](https://serverror.github.io/IL2-Mission-Planner/) e exporte o arquivo `.json`.
2. Arraste o arquivo para a Aba 1 da calculadora para definir a navegação.
3. Configure o peso e o combustível no hangar do jogo com base no painel verde.
4. Durante a aproximação do alvo, abra a Aba 2, insira os dados do vento passados pelo servidor e ajuste sua Lotfe 7 para um lançamento perfeito.

---
*Desenvolvido para a comunidade de simulação militar do IL-2 Sturmovik.*
