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

# 3. Construção da Interface
st.set_page_config(page_title="Painel He-111", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    header { background-color: transparent !important; }
    </style>
    """, unsafe_allow_html=True)

st.title("🛩️ Painel Tático de Voo: Heinkel He-111")
st.markdown("Calculadora integrada de combustível, engenharia estrutural e mira de bombardeamento.")

# Criação dos separadores
tab1, tab2 = st.tabs(["📊 Planeamento e Hangar", "🎯 Mira Lotfe 7 (Vento)"])

# ==========================================
# SEPARADOR 1: HANGAR E COMBUSTÍVEL
# ==========================================
with tab1:
    st.header("1. Plano de Voo (Opcional)")
    arquivo_plano = st.file_uploader("📥 Importar arquivo .json gerado no IL-2 Mission Planner", type=["json"])

    usar_dados_importados = False
    dist_calc = 250.0  
    vel_calc = 320.0

    if arquivo_plano is not None:
        try:
            dados_plano = json.load(arquivo_plano)
            rota = dados_plano["routes"][0]
            coords = rota["latLngs"]
            
            dist_total = 0.0
            for i in range(len(coords) - 1):
                p1 = coords[i]
                p2 = coords[i+1]
                dist_total += math.hypot(p2['lng'] - p1['lng'], p2['lat'] - p1['lat'])
            
            dist_calc = dist_total
            vel_calc = float(rota.get("
