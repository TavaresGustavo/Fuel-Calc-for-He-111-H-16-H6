import streamlit as st
import json
import math
import requests
import re

==========================================
# 0. FUNÇÃO DA API (TELEMETRIA AO VIVO)
# ==========================================
def fetch_combatbox_data():
    """Integração direta e invisível com a API JSON do Combat Box"""
    try:
        # A URL da API que o Gustavo encontrou!
        api_url = "https://campaign-data.combatbox.net/rhineland-campaign/rhineland-campaign-latest.json.aspx"
        
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(api_url, headers=headers, timeout=5)
        
        # Converte a resposta oficial em um dicionário Python
        dados_json = response.json()
        
        # Transformamos o dicionário em texto minúsculo para garantir 
        # que vamos achar os valores independentemente do nível da "árvore" JSON
        texto_json = json.dumps(dados_json).lower()
        
        # Busca blindada usando Regex direto nos valores do JSON
        temp_match = re.search(r'"temperature"\s*:\s*(-?[\d\.]+)', texto_json)
        vento_match = re.search(r'"windspeed"\s*:\s*([\d\.]+)', texto_json)
        dir_match = re.search(r'"winddirection"\s*:\s*([\d\.]+)', texto_json)
        
        # Plano B (Fallbacks) caso o desenvolvedor deles mude o nome da variável no futuro
        if not vento_match: vento_match = re.search(r'"wind_speed"\s*:\s*([\d\.]+)', texto_json)
        if not dir_match: dir_match = re.search(r'"wind_direction"\s*:\s*([\d\.]+)', texto_json)
        if not dir_match: dir_match = re.search(r'"winddir"\s*:\s*([\d\.]+)', texto_json)
        
        # Se encontrou a trindade da navegação, injeta na calculadora!
        if temp_match and vento_match and dir_match:
            st.session_state.temp_cb = float(temp_match.group(1))
            st.session_state.vento_vel_cb = float(vento_match.group(1))
            st.session_state.vento_dir_cb = float(dir_match.group(1))
            st.session_state.status_cb = "✅ API Sincronizada! Telemetria AO VIVO."
        else:
            st.session_state.status_cb = "⚠️ JSON recebido, mas variáveis de clima ausentes."
            
    except Exception as e:
        st.session_state.status_cb = f"❌ Falha de Conexão: {e}"

# ==========================================
# BARRA LATERAL (SIDEBAR) - VISUAL
# ==========================================
with st.sidebar:
    st.header("📡 Telemetria do Servidor")
    st.image("https://combatbox.net/static/img/combatbox_logo.png", width=200)
    st.markdown("Sincroniza a meteorologia da API do Combat Box com a calculadora.")
    
    if st.button("🔄 Puxar Dados (Combat Box)"):
        fetch_combatbox_data()
        
    st.caption(st.session_state.status_cb)
    st.divider()
    
    st.metric("Vento Dominante", f"{st.session_state.vento_vel_cb} m/s")
    st.metric("Direção do Vento", f"{st.session_state.vento_dir_cb}°")
    st.metric("Temperatura Local", f"{st.session_state.temp_cb} °C")
# ==========================================
# 1. BASE DE DADOS: Pesos e Aeronaves
# ==========================================
peso_bombas = {
    "SC 50": 50, "SC 250": 250, "SC 500": 500,
    "SC 1000": 1090, "SC 1800": 1780, "SC 2500": 2400  
}

db_avioes = {
    "He-111 H-6": {
        "peso_base_sem_combustivel": 9500,
        "peso_max": 14000, "consumo_l_min": 10.5, "vel_cruzeiro_padrao": 320, "tanque_max_l": 3450,
        "armamento_fixo": "6 x 7.92 mm MG-15",
        "modificacoes": {
            "Padrão (Sem torres 20mm)": 0, "Nose 20mm gun turret (+46 kg)": 46, "Belly 20mm gun turret (+147 kg)": 147, "Ambas as torres 20mm (+193 kg)": 193
        },
        "presets_bombas": {
            "Empty (Sem Bombas)": 0, "16 x SC 50": 16 * peso_bombas["SC 50"], "4 x SC 250": 4 * peso_bombas["SC 250"],
            "1 x SC 500 + 16 x SC 50": peso_bombas["SC 500"] + (16 * peso_bombas["SC 50"]), "2 x SC 1000": 2 * peso_bombas["SC 1000"],
            "1 x SC 1000 + 16 x SC 50": peso_bombas["SC 1000"] + (16 * peso_bombas["SC 50"]), "2 x SC 1800": 2 * peso_bombas["SC 1800"],
            "1 x SC 2500": peso_bombas["SC 2500"]
        }
    },
    "He-111 H-16": {
        "peso_base_sem_combustivel": 9300,
        "peso_max": 14000, "consumo_l_min": 10.2, "vel_cruzeiro_padrao": 330, "tanque_max_l": 3450,
        "armamento_fixo": "4x 7.92mm MG-15 | 1x 20mm MG/FF | 1x 13mm MG-131",
        "modificacoes": {"Padrão (Armamento Fixo Integrado)": 0},
        "presets_bombas": {
            "Empty (Sem Bombas)": 0, "16 x SC 50": 16 * peso_bombas["SC 50"], "32 x SC 50": 32 * peso_bombas["SC 50"],
            "4 x SC 250": 4 * peso_bombas["SC 250"], "8 x SC 250": 8 * peso_bombas["SC 250"], "2 x SC 500": 2 * peso_bombas["SC 500"],
            "2 x SC 1800": 2 * peso_bombas["SC 1800"], "1 x SC 2500": peso_bombas["SC 2500"]
        }
    },
    "Ju-52/3M": {
        "peso_base_sem_combustivel": 7500, 
        "peso_max": 11000, "consumo_l_min": 12.0, "vel_cruzeiro_padrao": 240, "tanque_max_l": 2450,   
        "armamento_fixo": "Nenhum (Transporte)",
        "modificacoes": {
            "Padrão (Sem carga interna, sem torre)": 0, "Rear turret (+130 kg)": 130, "2300 kg of cargo": 2300,
            "12 paratroopers (+1200 kg)": 1200, "12 paratroopers + Rear turret (+1330 kg)": 1330
        },
        "presets_bombas": {"Empty (Sem Drop Containers)": 0, "10 x MAB 250 containers": 2550}
    },
    "Ju-88 A-4": {
        "peso_base_sem_combustivel": 8600, 
        "peso_max": 14000, "consumo_l_min": 10.0, "vel_cruzeiro_padrao": 370, "tanque_max_l": 1680,   
        "armamento_fixo": "1x 13mm MG-131 | 4x 7.92mm MG-81/81Z",
        "modificacoes": {
            "Padrão": 0, "Remove dive brakes (-60 kg)": -60, "Armor plates for gunner (+20 kg)": 20, 
            "Remove lower gunner and gondola (-123 kg)": -123, "Remove lower gunner, gondola and dive brakes (-183 kg)": -183
        },
        "presets_bombas": {
            "Empty (Sem Bombas)": 0, "10 x SC 50": 10 * peso_bombas["SC 50"], "28 x SC 50": 28 * peso_bombas["SC 50"],
            "4 x SC 250": 4 * peso_bombas["SC 250"], "4 x SC 500": 4 * peso_bombas["SC 500"], "2 x SC 1000": 2 * peso_bombas["SC 1000"],
            "2 x SC 1800": 2 * peso_bombas["SC 1800"]
        }
    }
}

# ==========================================
# 2. CONFIGURAÇÃO DA INTERFACE & BARRA LATERAL
# ==========================================
st.set_page_config(page_title="Painel Tático", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #0E1117; color: #FAFAFA; }
    header { background-color: transparent !important; }
    .block-container { padding-top: 1.5rem !important; padding-bottom: 1rem !important; padding-left: 2rem !important; padding-right: 2rem !important; }
    [data-testid="stMetricValue"] { font-size: 1.3rem !important; color: #E2E2E2 !important; }
    [data-testid="stMetricLabel"] { font-size: 0.85rem !important; }
    h1 { font-size: 1.8rem !important; padding-bottom: 0.2rem !important; }
    h2 { font-size: 1.3rem !important; padding-bottom: 0.2rem !important; }
    div[data-testid="stVerticalBlock"] { gap: 0.5rem !important; }
    [data-testid="stAlert"] { padding: 0.5rem !important; }
    </style>
    """, unsafe_allow_html=True)

# BARRA LATERAL (SIDEBAR) - TELEMETRIA
with st.sidebar:
    st.header("📡 Telemetria do Servidor")
    st.image("https://combatbox.net/static/img/combatbox_logo.png", width=200) # Logo visual
    st.markdown("Sincroniza a meteorologia ao vivo do Combat Box diretamente com a calculadora.")
    
    if st.button("🔄 Puxar Dados (Combat Box)"):
        fetch_combatbox_data()
        
    st.caption(st.session_state.status_cb)
    st.divider()
    st.metric("Vento Dominante", f"{st.session_state.vento_vel_cb} m/s")
    st.metric("Direção do Vento", f"{st.session_state.vento_dir_cb}°")
    st.metric("Temperatura Local", f"{st.session_state.temp_cb} °C")


st.title("🛩️ Painel Tático de Voo")
tab1, tab2, tab3, tab4 = st.tabs(["📊 Planejamento e Hangar", "🎯 Mira Lotfe 7", "🧮 Computador E6B", "🌐 Inteligência (Combat Box)"])

# ==========================================
# 3. SEPARADOR 1: HANGAR E COMBUSTÍVEL
# ==========================================
usar_dados_importados = False
coords = []
dist_calc = 250.0  
vel_calc = 320.0

with tab1:
    st.header("1. Plano de Voo (Opcional)")
    arquivo_plano = st.file_uploader("📥 Importar ficheiro .json gerado no IL-2 Mission Planner", type=["json"])

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
            
            dist_calc = dist_total * 3.0 
            vel_calc = float(rota.get("speed", 320.0))
            nome_rota = rota.get("name", "Missão Importada")
            usar_dados_importados = True
            
            st.success(f"✅ Rota '{nome_rota}' importada com sucesso!")
        except Exception as e:
            st.error("Erro ao ler o ficheiro JSON.")

    st.divider()
    col_esq, col_dir = st.columns([1, 1])

    with col_esq:
        st.header("2. Navegação Global")
        modelo_selecionado = st.selectbox("Versão da Aeronave", list(db_avioes.keys()))
        aviao = db_avioes[modelo_selecionado]
        
        if usar_dados_importados:
            distancia_km = st.number_input("Distância Total (km)", value=float(dist_calc), disabled=True, key="dist_lock")
            velocidade_estimada = st.number_input("Velocidade Média (km/h)", value=float(vel_calc), disabled=True, key="vel_lock")
        else:
            distancia_km = st.number_input("Distância Total (km)", min_value=1.0, value=250.0, key="dist_free")
            velocidade_estimada = st.number_input("Velocidade Média (km/h)", min_value=150.0, value=float(aviao['vel_cruzeiro_padrao']), key="vel_free")
        
        margem_reserva = st.slider("Reserva de Combate (%)", min_value=0, max_value=150, value=90, step=5)

    with col_dir:
        st.header("3. Hangar (Loadout)")
        mod_selecionada = st.selectbox("Modificações de Armamento", list(aviao["modificacoes"].keys()))
        peso_mods = aviao["modificacoes"][mod_selecionada]
        
        preset_selecionado = st.selectbox("Preset de Bombas/Carga", list(aviao["presets_bombas"].keys()))
        peso_bombas_total = aviao["presets_bombas"][preset_selecionado]

    tempo_voo_min = (distancia_km / velocidade_estimada) * 60
    combustivel_necessario = tempo_voo_min * aviao["consumo_l_min"]
    combustivel_com_reserva = combustivel_necessario * (1 + (margem_reserva / 100))
    porcentagem_tanque = min((combustivel_com_reserva / aviao["tanque_max_l"]) * 100, 100.0)
    peso_combustivel = combustivel_com_reserva * 0.72 
    peso_total_decolagem = aviao["peso_base_sem_combustivel"] + peso_mods + peso_bombas_total + peso_combustivel

    st.divider()
    res_col1, res_col2, res_col3 = st.columns(3)
    with res_col1:
        st.warning(f"🛢️ Combustível: {porcentagem_tanque:.1f}% ({combustivel_com_reserva:.0f} L)")
    with res_col2:
        st.info(f"⏱️ Tempo Total: {tempo_voo_min:.0f} min")
    with res_col3:
        st.error(f"💣 Carga Paga: {peso_bombas_total + peso_mods:.0f} kg")

    if peso_total_decolagem <= aviao["peso_max"]:
        st.success(f"✅ DESCOLAGEM AUTORIZADA: {peso_total_decolagem:.0f} kg / {aviao['peso_max']} kg")
    else:
        st.error(f"❌ SOBRECARGA CRÍTICA! {peso_total_decolagem:.0f} kg excede o limite.")

# ==========================================
# 4. SEPARADOR 2: MIRA LOTFE 7
# ==========================================
with tab2:
    st.header("🎯 Calculadora Balística (Lotfe 7)")
    st.caption("As caixas de vento alimentam-se automaticamente da telemetria da barra lateral.")
    b_col1, b_col2 = st.columns(2)
    with b_col1:
        altitude = st.number_input("Altitude (Metros)", min_value=500, value=3000, step=100)
        ias = st.number_input("IAS (km/h)", min_value=150, value=280, step=10)
        proa_alvo = st.number_input("Proa do Alvo (°)", min_value=0, max_value=360, value=90, step=1)
    with b_col2:
        # Repara que o value está amarrado ao session_state!
        vel_vento = st.number_input("Vel. do Vento (m/s)", value=float(st.session_state.vento_vel_cb), step=1.0)
        dir_vento = st.number_input("Vento soprar DE (°)", value=float(st.session_state.vento_dir_cb), step=1.0)

    tas_ms = (ias * (1 + (altitude / 1000) * 0.05)) / 3.6
    angulo_vento_rad = math.radians(dir_vento - proa_alvo)
    
    try:
        sin_deriva = max(-1.0, min(1.0, (vel_vento * math.sin(angulo_vento_rad)) / tas_ms))
        deriva_graus = math.degrees(math.asin(sin_deriva))
    except:
        deriva_graus = 0.0

    gs_kmh = ((tas_ms * math.cos(math.radians(deriva_graus))) - (vel_vento * math.cos(angulo_vento_rad))) * 3.6

    st.divider()
    r_col1, r_col2, r_col3 = st.columns(3)
    r_col1.metric("TAS (Vel. Verdadeira)", f"{tas_ms * 3.6:.0f} km/h")
    r_col2.metric("GS (Vel. no Solo)", f"{gs_kmh:.0f} km/h")
    direcao_deriva = "Direita" if deriva_graus > 0 else "Esquerda" if deriva_graus < 0 else "Nenhuma"
    r_col3.metric("Ângulo de Deriva", f"{abs(deriva_graus):.1f}° {direcao_deriva}")

# ==========================================
# 5. SEPARADOR 3: E6B NAVLOG & DENSITY ALTITUDE
# ==========================================
with tab3:
    st.header("🧮 Computador de Voo E6B")
    
    if usar_dados_importados and len(coords) > 1:
        st.subheader("🗺️ Diário de Navegação (NavLog)")
        w_col1, w_col2, w_col3 = st.columns(3)
        with w_col1:
            nav_tas = st.number_input("Sua TAS (km/h)", value=float(vel_calc), step=10.0)
        with w_col2:
            nav_w_dir = st.number_input("Vento vindo DE (°)", value=float(st.session_state.vento_dir_cb))
        with w_col3:
            # Converter o vento de m/s da API para km/h no NavLog
            nav_w_spd = st.number_input("Vel. Vento (km/h)", value=float(st.session_state.vento_vel_cb * 3.6))

        navlog = []
        for i in range(len(coords) - 1):
            p1 = coords[i]
            p2 = coords[i+1]
            dx = p2['lng'] - p1['lng']
            dy = p2['lat'] - p1['lat']

            dist_leg = math.hypot(dx, dy) * 3.0
            tc_rad = math.atan2(dx, -dy) 
            tc_deg = (math.degrees(tc_rad) + 360) % 360

            wa_rad = math.radians(nav_w_dir - tc_deg)
            try:
                sin_wca = max(-1.0, min(1.0, (nav_w_spd * math.sin(wa_rad)) / nav_tas))
                wca_rad = math.asin(sin_wca)
                wca_deg = math.degrees(wca_rad)
            except:
                wca_deg = 0.0

            th_deg = (tc_deg + wca_deg + 360) % 360
            gs_leg = (nav_tas * math.cos(wca_rad)) - (nav_w_spd * math.cos(wa_rad))
            gs_leg = max(1.0, gs_leg)
            
            tempo_leg_min = (dist_leg / gs_leg) * 60

            navlog.append({
                "Perna": f"WP{i} ➔ WP{i+1}",
                "Dist. (km)": f"{dist_leg:.1f}",
                "Rota no Mapa": f"{tc_deg:.0f}°",
                "Proa Corrigida": f"{th_deg:.0f}°",
                "GS (km/h)": f"{gs_leg:.0f}",
                "Tempo (min)": f"{tempo_leg_min:.1f}"
            })

        st.table(navlog)
    else:
        st.info("📥 Importe um plano de voo (JSON) na Aba 1 para gerar o Diário de Navegação (NavLog) automático.")

    st.divider()
    
    # NOVAS FUNÇÕES: ALTITUDE DE DENSIDADE E CONVERSÕES
    st.subheader("🌡️ Performance: Altitude de Densidade")
    st.markdown("Calcula a altitude real que os teus motores 'sentem' com base na temperatura.")
    d1, d2, d3 = st.columns(3)
    with d1:
        ele_campo = st.number_input("Elevação da Pista (pés)", value=500.0, step=100.0)
    with d2:
        oat = st.number_input("Temp. Externa (°C)", value=float(st.session_state.temp_cb), step=1.0)
    with d3:
        # Fórmula Padrão de Altitude de Densidade
        isa_temp = 15 - (2 * (ele_campo / 1000))
        da_calc = ele_campo + (120 * (oat - isa_temp))
        st.metric("Altitude de Densidade (DA)", f"{da_calc:.0f} pés")
        if da_calc > ele_campo + 1000:
            st.caption("⚠️ **Atenção:** O ar está rarefeito. Exigirá mais pista para descolar!")

    st.divider()
    
    st.subheader("🔄 Conversor Universal E6B")
    c1, c2, c3 = st.columns(3)
    with c1:
        vel_input = st.number_input("Velocidade", value=300.0)
        st.caption(f"**{vel_input} km/h** = {vel_input / 1.60934:.0f} mph")
        st.caption(f"**{vel_input} mph** = {vel_input * 1.60934:.0f} km/h")
    with c2:
        alt_input = st.number_input("Dist. / Altitude", value=1000.0)
        st.caption(f"**{alt_input} metros** = {alt_input * 3.28084:.0f} pés")
        st.caption(f"**{alt_input} pés** = {alt_input / 3.28084:.0f} metros")
    with c3:
        peso_input = st.number_input("Peso / Volume", value=100.0)
        st.caption(f"**{peso_input} kg** = {peso_input * 2.20462:.0f} lbs")
        st.caption(f"**{peso_input} galões** = {peso_input * 3.78541:.1f} litros")

# ==========================================
# 6. SEPARADOR 4: INTELIGÊNCIA E RADAR (C4ISR)
# ==========================================
with tab4:
    st.header("🌐 Painel de Inteligência Global")
    st.markdown("Análise de telemetria avançada, logística e alvos ativos extraídos do servidor.")
    
    if st.button("📡 Atualizar Radar & Logística", key="btn_radar"):
        # Fazemos um request direto ao JSON completo da campanha
        try:
            api_url = "https://campaign-data.combatbox.net/rhineland-campaign/rhineland-campaign-latest.json.aspx"
            response = requests.get(api_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=8)
            st.session_state.dados_campanha = response.json()
            st.success("✅ Banco de dados tático atualizado!")
        except Exception as e:
            st.error(f"❌ Erro ao ligar ao servidor de campanha: {e}")

    st.divider()

    # Se já tivermos o JSON carregado na memória, começamos a mineração de dados
    if 'dados_campanha' in st.session_state and st.session_state.dados_campanha:
        dados = st.session_state.dados_campanha
        
        col_w, col_t = st.columns([1, 2])
        
        # --- BLOCO METEOROLÓGICO AVANÇADO ---
        with col_w:
            st.subheader("⛅ Meteorologia")
            # Procura dados de nuvens e clima dentro do JSON
            # Nota: As chaves exatas (ex: 'Weather', 'Clouds') dependem da estrutura do Combat Box
            clima = dados.get('Weather', {}) 
            if not clima:
                # Fallback caso a chave tenha outro nome na raiz do JSON
                clima = dados
                
            nuvens_base = clima.get('CloudBase', 'N/D')
            pressao = clima.get('Pressure', 'N/D')
            
            st.metric("Base das Nuvens (Teto)", f"{nuvens_base} m")
            st.metric("Pressão (QNH)", f"{pressao} mmHg")
            
            st.markdown("**Vento em Altitude:**")
            st.info("A aguardar mapeamento de camadas...") # Expandiremos se o JSON tiver array de ventos
            
        # --- BLOCO DE ALVOS ATIVOS ---
        with col_t:
            st.subheader("🎯 Alvos Estratégicos (Ativos)")
            alvos = dados.get('Targets', [])
            alvos_ativos = [t for t in alvos if t.get('Status') != 'Destroyed']
            
            if alvos_ativos:
                for alvo in alvos_ativos[:5]: # Mostra os 5 primeiros para não poluir
                    nome = alvo.get('Name', 'Alvo Desconhecido')
                    tipo = alvo.get('Type', 'Instalação')
                    st.warning(f"**{nome}** ({tipo}) - Status: Operacional")
            else:
                st.caption("A processar a lista de alvos da base de dados. Pressione Atualizar.")
                
        st.divider()
        
        # --- BLOCO DE LOGÍSTICA (AERÓDROMOS) ---
        st.subheader("🛫 Logística de Base")
        aerodromos = dados.get('Airfields', [])
        
        if aerodromos:
            nomes_bases = [a.get('Name', 'Base S/N') for a in aerodromos]
            base_selecionada = st.selectbox("Selecione um Aeródromo para inspecionar:", nomes_bases)
            
            # Filtra o aeródromo selecionado
            base_dados = next((a for a in aerodromos if a.get('Name') == base_selecionada), None)
            
            if base_dados:
                st.markdown(f"**Facção:** {base_dados.get('Coalition', 'Desconhecida')}")
                avioes = base_dados.get('Aircraft', [])
                if avioes:
                    st.write("Aeronaves Disponíveis no Hangar:")
                    # Cria colunas dinâmicas para listar os aviões
                    cols = st.columns(3)
                    for i, aviao in enumerate(avioes):
                        cols[i % 3].metric(aviao.get('Type', 'Aeronave'), f"{aviao.get('Count', 0)} unid.")
                else:
                    st.caption("Sem dados de estoque para esta base.")
        else:
            st.caption("Estrutura de aeródromos a aguardar mapeamento exato das chaves do JSON.")

    else:
        st.info("Pressione o botão acima para extrair o banco de dados do servidor.")
