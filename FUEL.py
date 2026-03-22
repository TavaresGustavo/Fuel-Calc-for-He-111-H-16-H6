import streamlit as st
import json
import math

# 1. Pesos Reais Extraídos do IL-2 (em kg)
peso_bombas = {
    "SC 50": 50, "SC 250": 250, "SC 500": 500,
    "SC 1000": 1090, "SC 1800": 1780, "SC 2500": 2400  
}

# 2. Banco de Dados Oficial: He-111
db_avioes = {
    "He-111 H-6": {
        "peso_vazio": 13727, "peso_max": 15239, "consumo_l_min": 10.5,
        "vel_cruzeiro_padrao": 320, "tanque_max_l": 3450,
        "armamento_fixo": "6 x 7.92 mm MG-15",
        "modificacoes": {
            "Padrão (Sem torres 20mm)": 0,
            "Nose 20mm gun turret (+46 kg)": 46,
            "Belly 20mm gun turret (+147 kg)": 147,
            "Ambas as torres 20mm (+193 kg)": 193
        },
        "presets_bombas": {
            "№14: Empty (Sem Bombas)": 0,
            "№1: 16 x SC 50": 16 * peso_bombas["SC 50"],
            "№2: 4 x SC 250": 4 * peso_bombas["SC 250"],
            "№3: 1 x SC 500 + 16 x SC 50": peso_bombas["SC 500"] + (16 * peso_bombas["SC 50"]),
            "№4: 1 x SC 500 + 4 x SC 250": peso_bombas["SC 500"] + (4 * peso_bombas["SC 250"]),
            "№5: 2 x SC 1000": 2 * peso_bombas["SC 1000"],
            "№6: 1 x SC 1000 + 16 x SC 50": peso_bombas["SC 1000"] + (16 * peso_bombas["SC 50"]),
            "№7: 1 x SC 1000 + 4 x SC 250": peso_bombas["SC 1000"] + (4 * peso_bombas["SC 250"]),
            "№8: 2 x SC 1800": 2 * peso_bombas["SC 1800"],
            "№9: 1 x SC 1800 + 16 x SC 50": peso_bombas["SC 1800"] + (16 * peso_bombas["SC 50"]),
            "№10: 1 x SC 1800 + 4 x SC 250": peso_bombas["SC 1800"] + (4 * peso_bombas["SC 250"]),
            "№12: 1 x SC 2500": peso_bombas["SC 2500"]
        }
    },
    "He-111 H-16": {
        "peso_vazio": 13017, "peso_max": 15689, "consumo_l_min": 10.2,
        "vel_cruzeiro_padrao": 330, "tanque_max_l": 3450,
        "armamento_fixo": "4x 7.92mm MG-15 | 1x 20mm MG/FF | 1x 13mm MG-131",
        "modificacoes": {
            "Padrão (Armamento Fixo Integrado)": 0
        },
        "presets_bombas": {
            "№20: Empty (Sem Bombas)": 0,
            "№1: 16 x SC 50": 16 * peso_bombas["SC 50"],
            "№2: 32 x SC 50": 32 * peso_bombas["SC 50"],
            "№3: 4 x SC 250": 4 * peso_bombas["SC 250"],
            "№4: 8 x SC 250": 8 * peso_bombas["SC 250"],
            "№5: 4 x SC 250 + 16 x SC 50": (4 * peso_bombas["SC 250"]) + (16 * peso_bombas["SC 50"]),
            "№6: 1 x SC 500 + 16 x SC 50": peso_bombas["SC 500"] + (16 * peso_bombas["SC 50"]),
            "№7: 1 x SC 500 + 4 x SC 250": peso_bombas["SC 500"] + (4 * peso_bombas["SC 250"]),
            "№8: 2 x SC 500": 2 * peso_bombas["SC 500"],
            "№12: 1 x SC 1800 + 16 x SC 50": peso_bombas["SC 1800"] + (16 * peso_bombas["SC 50"]),
            "№13: 1 x SC 1800 + 4 x SC 250": peso_bombas["SC 1800"] + (4 * peso_bombas["SC 250"]),
            "№14: 2 x SC 1800": 2 * peso_bombas["SC 1800"],
            "№16: 1 x SC 2500": peso_bombas["SC 2500"],
            "№17: 1 x SC 2500 + 16 x SC 50": peso_bombas["SC 2500"] + (16 * peso_bombas["SC 50"]),
            "№18: 1 x SC 2500 + 4 x SC 250": peso_bombas["SC 2500"] + (4 * peso_bombas["SC 250"])
        }
    }
}

# 3. Construção da Interface com Dark Mode Forçado
st.set_page_config(page_title="Painel He-111", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    header { background-color: transparent !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛩️ Painel Tático de Voo: Heinkel He-111")
st.markdown("Calculadora balística e de combustível (Sincronizada com IL-2 Mission Planner)")

# --- NOVO: MÓDULO DE IMPORTAÇÃO DE VOO ---
st.header("1. Plano de Voo (Opcional)")
arquivo_plano = st.file_uploader("📥 Importar arquivo .json gerado no IL-2 Mission Planner", type=["json"])

usar_dados_importados = False
dist_calc = 250.0  # Valores default manuais
vel_calc = 320.0

if arquivo_plano is not None:
    try:
        dados_plano = json.load(arquivo_plano)
        rota = dados_plano["routes"][0]
        coords = rota["latLngs"]
        
        # Calcular distância total somando a distância euclidiana entre os waypoints
        dist_total = 0.0
        for i in range(len(coords) - 1):
            p1 = coords[i]
            p2 = coords[i+1]
            dist_total += math.hypot(p2['lng'] - p1['lng'], p2['lat'] - p1['lat'])
        
        dist_calc = dist_total
        vel_calc = float(rota.get("speed", 320.0))
        nome_rota = rota.get("name", "Missão Importada")
        usar_dados_importados = True
        
        st.success(f"✅ Rota '{nome_rota}' importada! Os dados de Navegação foram travados com as definições do arquivo.")
    except Exception as e:
        st.error("Erro ao ler o arquivo JSON. Certifique-se de que é o export correto do Mission Planner.")

st.divider()

col_esq, col_dir = st.columns([1, 1])

with col_esq:
    st.header("2. Navegação")
    modelo_selecionado = st.selectbox("Versão da Aeronave", list(db_avioes.keys()))
    aviao = db_avioes[modelo_selecionado]
    st.caption(f"**Armamento Fixo:** {aviao['armamento_fixo']}")
    
    # Se não importar dados, puxa a velocidade padrão da aeronave selecionada
    if not usar_dados_importados:
        vel_calc = float(aviao['vel_cruzeiro_padrao'])
    
    # As caixas ficam desativadas automaticamente se um arquivo for carregado
    distancia_km = st.number_input("Distância Total da Rota (km)", min_value=1.0, max_value=5000.0, value=float(dist_calc), disabled=usar_dados_importados)
    velocidade_estimada = st.number_input("Velocidade Média Estimada (km/h)", min_value=150.0, max_value=450.0, value=float(vel_calc), disabled=usar_dados_importados)
    
    margem_reserva = st.slider("Reserva Extra de Combustível (%)", min_value=0, max_value=150, value=90, step=5)

with col_dir:
    st.header("3. Hangar (Loadout)")
    mod_selecionada = st.selectbox("Modificações de Armamento", list(aviao["modificacoes"].keys()))
    peso_mods = aviao["modificacoes"][mod_selecionada]
    
    preset_selecionado = st.selectbox("Selecione o Preset de Bombas", list(aviao["presets_bombas"].keys()))
    peso_bombas_total = aviao["presets_bombas"][preset_selecionado]

# 4. Motor de Cálculo
st.divider()

tempo_voo_min = (distancia_km / velocidade_estimada) * 60
combustivel_necessario = tempo_voo_min * aviao["consumo_l_min"]

multiplicador_reserva = 1 + (margem_reserva / 100)
combustivel_com_reserva = combustivel_necessario * multiplicador_reserva

porcentagem_tanque = (combustivel_com_reserva / aviao["tanque_max_l"]) * 100
if porcentagem_tanque > 100: porcentagem_tanque = 100

peso_combustivel = combustivel_com_reserva * 0.72
peso_total_decolagem = aviao["peso_vazio"] + peso_mods + peso_bombas_total + peso_combustivel

# 5. Dashboard Visual
st.header("4. Relatório Final de Voo")

res_col1, res_col2, res_col3 = st.columns(3)

with res_col1:
    st.info("⏱️ DADOS DO MAPA")
    st.metric(label="Tempo Estimado de Voo", value=f"{tempo_voo_min:.0f} min")
    st.metric(label="Distância a Percorrer", value=f"{distancia_km:.1f} km")

with res_col2:
    st.warning("🛢️ COMBUSTÍVEL")
    st.metric(label=f"Litros Necessários (+{margem_reserva}%)", value=f"{combustivel_com_reserva:.0f} L")
    st.metric(label="Ajuste no Hangar (%)", value=f"{porcentagem_tanque:.1f} %")

with res_col3:
    st.error("💣 CARGA ÚTIL")
    st.metric(label="Peso das Bombas", value=f"{peso_bombas_total:.0f} kg")
    st.metric(label="Peso Estrutural Extra (Mods)", value=f"{peso_mods:.0f} kg")

st.subheader("⚖️ Status Estrutural de Decolagem")
proporcao = peso_total_decolagem / aviao["peso_max"]

if peso_total_decolagem <= aviao["peso_max"]:
    st.progress(proporcao)
    st.success(f"✅ DECOLAGEM AUTORIZADA: Peso de {peso_total_decolagem:.0f} kg. (Limite Estritural: {aviao['peso_max']} kg).")
else:
    st.progress(1.0)
    excesso = peso_total_decolagem - aviao["peso_max"]
    st.error(f"❌ SOBRECARGA CRÍTICA! Peso de {peso_total_decolagem:.0f} kg excede o limite em {excesso:.0f} kg.")
    st.caption("Ação Necessária: Diminua a reserva de combustível ou selecione um preset de bombas mais leve para esta rota.")