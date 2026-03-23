import streamlit as st
import json
import math
import requests
import time

# ==========================================
# 0. INICIALIZAÇÃO DA MEMÓRIA (SESSION STATE)
# ==========================================
# Variáveis de HOJE (Alimentam a Lotfe 7)
if 'vento_vel_cb' not in st.session_state: st.session_state.vento_vel_cb = 5.0
if 'vento_dir_cb' not in st.session_state: st.session_state.vento_dir_cb = 45.0
if 'temp_cb' not in st.session_state: st.session_state.temp_cb = 15.0
if 'nuvens_hoje_cb' not in st.session_state: st.session_state.nuvens_hoje_cb = "Desconhecido"

# Variáveis de AMANHÃ (Previsão)
if 'vento_vel_amanha_cb' not in st.session_state: st.session_state.vento_vel_amanha_cb = 5.0
if 'vento_dir_amanha_cb' not in st.session_state: st.session_state.vento_dir_amanha_cb = 45.0
if 'temp_amanha_cb' not in st.session_state: st.session_state.temp_amanha_cb = 15.0
if 'nuvens_amanha_cb' not in st.session_state: st.session_state.nuvens_amanha_cb = "Desconhecido"

if 'status_cb' not in st.session_state: st.session_state.status_cb = "A aguardar sincronização..."
if 'dados_campanha' not in st.session_state: st.session_state.dados_campanha = None

# ==========================================
# 1. FUNÇÃO DA API JSON (SEPARAÇÃO HOJE/AMANHÃ)
# ==========================================
def fetch_combatbox_data():
    """Extrai os dados da missão atual e a previsão do dia seguinte"""
    try:
        api_url = "https://campaign-data.combatbox.net/rhineland-campaign/rhineland-campaign-latest.json.aspx"
        response = requests.get(api_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=8)
        
        if response.status_code != 200:
            st.session_state.status_cb = f"❌ Erro HTTP {response.status_code}"
            return
            
        dados_json = response.json()
        st.session_state.dados_campanha = dados_json 
        
        # 1. Extração do Clima de HOJE (Atual)
        weather_hoje = dados_json.get("Weather", {})
        wind_hoje = weather_hoje.get("WindAtGroundLevel", {})
        
        st.session_state.temp_cb = float(weather_hoje.get("Temperature", 15.0))
        st.session_state.vento_vel_cb = float(wind_hoje.get("Speed", 5.0))
        st.session_state.vento_dir_cb = float(wind_hoje.get("Bearing", 45.0))
        st.session_state.nuvens_hoje_cb = weather_hoje.get("CloudDescription", "N/D")

        # 2. Extração do Clima de AMANHÃ (Previsão)
        weather_amanha = dados_json.get("WeatherTomorrow", {})
        wind_amanha = weather_amanha.get("WindAtGroundLevel", {})
        
        st.session_state.temp_amanha_cb = float(weather_amanha.get("Temperature", 15.0))
        st.session_state.vento_vel_amanha_cb = float(wind_amanha.get("Speed", 5.0))
        st.session_state.vento_dir_amanha_cb = float(wind_amanha.get("Bearing", 45.0))
        st.session_state.nuvens_amanha_cb = weather_amanha.get("CloudDescription", "N/D")
        
        st.session_state.status_cb = "✅ API Sincronizada! Telemetria AO VIVO."
            
    except Exception as e:
        st.session_state.status_cb = f"❌ Erro de Ligação: {e}"

# ==========================================
# 2. BASE DE DADOS: Pesos e Aeronaves
# ==========================================
peso_bombas = {"SC 50": 50, "SC 250": 250, "SC 500": 500, "SC 1000": 1090, "SC 1800": 1780, "SC 2500": 2400}

db_avioes = {
    "He-111 H-6": {
        "peso_base_sem_combustivel": 9500, "peso_max": 14000, "consumo_l_min": 10.5, "vel_cruzeiro_padrao": 320, "tanque_max_l": 3450,
        "armamento_fixo": "6 x 7.92 mm MG-15",
        "modificacoes": {"Padrão": 0, "Torre Frontal": 46, "Torre Ventral": 147, "Ambas": 193},
        "presets_bombas": {"Vazio": 0, "16x SC 50": 800, "4x SC 250": 1000, "2x SC 1000": 2180}
    },
    "Ju-52/3M": {
        "peso_base_sem_combustivel": 7500, "peso_max": 11000, "consumo_l_min": 12.0, "vel_cruzeiro_padrao": 240, "tanque_max_l": 2450,   
        "armamento_fixo": "Transporte",
        "modificacoes": {"Padrão": 0, "Torre Traseira": 130, "Carga Interna (2300kg)": 2300, "12 Paraquedistas (1200kg)": 1200},
        "presets_bombas": {"Vazio": 0, "10x MAB 250": 2550}
    },
    "Ju-88 A-4": {
        "peso_base_sem_combustivel": 8600, "peso_max": 14000, "consumo_l_min": 10.0, "vel_cruzeiro_padrao": 370, "tanque_max_l": 1680,   
        "armamento_fixo": "1x 13mm | 4x 7.92mm",
        "modificacoes": {"Padrão": 0, "Sem Dive Brakes": -60, "Sem Gôndola Inferior": -123},
        "presets_bombas": {"Vazio": 0, "10x SC 50": 500, "4x SC 250": 1000, "4x SC 500": 2000}
    }
}

# ==========================================
# 3. INTERFACE E BARRA LATERAL (AUTO-REFRESH)
# ==========================================
st.set_page_config(page_title="Painel Tático", layout="wide")
st.markdown("""<style>.stApp { background-color: #0E1117; color: #FAFAFA; }</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.header("📡 Comando e Controlo")
    st.markdown("Telemetria em tempo real (Atualiza a cada 60s).")
    
    @st.fragment(run_every="60s")
    def painel_telemetria_ativo():
        fetch_combatbox_data()
        st.info(st.session_state.status_cb)
        st.divider()
        st.markdown("**METEOROLOGIA: MISSÃO ATUAL**")
        st.metric("Vento Dominante", f"{st.session_state.vento_vel_cb} m/s")
        st.metric("Direção do Vento", f"{st.session_state.vento_dir_cb}°")
        st.metric("Temperatura Local", f"{st.session_state.temp_cb} °C")
        st.caption(f"⏱️ Última sincronização: {time.strftime('%H:%M:%S')}")
        
    painel_telemetria_ativo()

st.title("🛩️ Painel Tático C4ISR")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Hangar", "🎯 Lotfe 7", "🧮 NavLog", "🌐 Inteligência Global", "🛠️ Debug API"])

# ==========================================
# ABA 1: HANGAR
# ==========================================
usar_dados_importados = False
coords = []
dist_calc = 250.0  
vel_calc = 320.0

with tab1:
    arquivo_plano = st.file_uploader("📥 Importar .json do Mission Planner", type=["json"])
    if arquivo_plano is not None:
        try:
            dados_plano = json.load(arquivo_plano)
            if "routes" in dados_plano and len(dados_plano["routes"]) > 0 and "latLngs" in dados_plano["routes"][0]:
                rota = dados_plano["routes"][0]
                coords = rota["latLngs"]
                dist_total = sum(math.hypot(coords[i+1]['lng'] - coords[i]['lng'], coords[i+1]['lat'] - coords[i]['lat']) for i in range(len(coords)-1))
                dist_calc = dist_total * 3.0 
                vel_calc = float(rota.get("speed", 320.0))
                usar_dados_importados = True
                st.success("✅ Rota tática importada!")
        except:
            st.error("Erro ao ler JSON.")

    col_esq, col_dir = st.columns(2)
    with col_esq:
        aviao = db_avioes[st.selectbox("Aeronave", list(db_avioes.keys()))]
        distancia_km = st.number_input("Distância (km)", value=float(dist_calc), disabled=usar_dados_importados)
        velocidade_estimada = st.number_input("Velocidade (km/h)", value=float(vel_calc), disabled=usar_dados_importados)
        margem_reserva = st.slider("Reserva (%)", 0, 150, 90)

    with col_dir:
        peso_mods = aviao["modificacoes"][st.selectbox("Modificações", list(aviao["modificacoes"].keys()))]
        peso_bombas_total = aviao["presets_bombas"][st.selectbox("Bombas", list(aviao["presets_bombas"].keys()))]

    combustivel_com_reserva = ((distancia_km / velocidade_estimada) * 60) * aviao["consumo_l_min"] * (1 + (margem_reserva / 100))
    peso_total = aviao["peso_base_sem_combustivel"] + peso_mods + peso_bombas_total + (combustivel_com_reserva * 0.72)

    st.divider()
    if peso_total <= aviao["peso_max"]:
        st.success(f"✅ DECOLAGEM AUTORIZADA: {peso_total:.0f} kg / {aviao['peso_max']} kg")
    else:
        st.error(f"❌ SOBRECARGA: {peso_total:.0f} kg excede limite de {aviao['peso_max']} kg.")

# ==========================================
# ABA 2: LOTFE 7 E ABA 3: NAVLOG
# ==========================================
with tab2:
    b1, b2 = st.columns(2)
    with b1:
        altitude = st.number_input("Altitude (m)", value=3000)
        ias = st.number_input("IAS (km/h)", value=280)
        proa_alvo = st.number_input("Proa (°)", value=90)
    with b2:
        # Puxa automaticamente o clima de HOJE!
        vel_vento = st.number_input("Vel. Vento (m/s)", value=float(st.session_state.vento_vel_cb))
        dir_vento = st.number_input("Dir. Vento (°)", value=float(st.session_state.vento_dir_cb))

    tas_ms = (ias * (1 + (altitude / 1000) * 0.05)) / 3.6
    ang_vento_rad = math.radians(dir_vento - proa_alvo)
    try: deriva_graus = math.degrees(math.asin(max(-1.0, min(1.0, (vel_vento * math.sin(ang_vento_rad)) / tas_ms))))
    except: deriva_graus = 0.0
    gs_kmh = ((tas_ms * math.cos(math.radians(deriva_graus))) - (vel_vento * math.cos(ang_vento_rad))) * 3.6
    
    st.metric("Insira na Lotfe: Velocidade Solo (GS)", f"{gs_kmh:.0f} km/h")
    st.metric("Insira na Lotfe: Ângulo de Deriva", f"{abs(deriva_graus):.1f}° {'Direita' if deriva_graus > 0 else 'Esquerda'}")

with tab3:
    if usar_dados_importados and len(coords) > 1:
        navlog = []
        for i in range(len(coords) - 1):
            dx, dy = coords[i+1]['lng'] - coords[i]['lng'], coords[i+1]['lat'] - coords[i]['lat']
            dist = math.hypot(dx, dy) * 3.0
            tc_deg = (math.degrees(math.atan2(dx, -dy)) + 360) % 360
            navlog.append({"Perna": f"WP{i}➔WP{i+1}", "Dist.": f"{dist:.1f} km", "Rumo (Mapa)": f"{tc_deg:.0f}°"})
        st.table(navlog)
    else:
        st.info("Importe um Plano de Voo na Aba 1 para gerar o NavLog.")

# ==========================================
# ABA 4: INTELIGÊNCIA GLOBAL (C4ISR)
# ==========================================
with tab4:
    st.header("🌐 Inteligência Tática e Logística")
    if st.session_state.dados_campanha:
        dados = st.session_state.dados_campanha
        
        st.subheader("⛅ Quadro Meteorológico")
        c_hoje, c_amanha = st.columns(2)
        
        with c_hoje:
            st.info(f"**MISSÃO ATUAL (HOJE)**\n\nNuvens: {st.session_state.nuvens_hoje_cb}\n\nTemp: {st.session_state.temp_cb} °C | Vento: {st.session_state.vento_vel_cb} m/s a {st.session_state.vento_dir_cb}°")
        with c_amanha:
            st.warning(f"**PRÓXIMA MISSÃO (AMANHÃ)**\n\nNuvens: {st.session_state.nuvens_amanha_cb}\n\nTemp: {st.session_state.temp_amanha_cb} °C | Vento: {st.session_state.vento_vel_amanha_cb} m/s a {st.session_state.vento_dir_amanha_cb}°")
            
        st.caption(f"Situação da Guerra: {dados.get('CurrentDayStateDescription', 'Não informada.')}")
        st.divider()
        
        col_t, col_b = st.columns([1, 1])
        with col_t:
            st.subheader("🎯 Objetivos Terrestres")
            objetivos = dados.get('Objectives', [])
            objetivos_ativos = [o for o in objetivos if o.get('ActiveToday') == True]
            for obj in objetivos_ativos[:6]:
                st.error(f"**{obj.get('Name', 'Alvo')}** ({obj.get('Type', 'Instalação')})")
                
        with col_b:
            st.subheader("🛫 Logística de Base")
            bases = dados.get('Airfields', [])
            if bases:
                base_sel = st.selectbox("Inspecionar Estoque:", [b.get('Name', 'Base') for b in bases])
                dados_base = next((b for b in bases if b.get('Name') == base_sel), None)
                if dados_base:
                    avioes_base = dados_base.get('AvailableAirframes', [])
                    if avioes_base:
                        for av in avioes_base:
                            st.write(f"- {av.get('ColloquialName', av.get('Type', 'Aeronave'))}: **{av.get('NumberAvailable', 0)}** unid.")
                    else:
                        st.write("Sem aeronaves listadas.")
    else:
        st.info("Aguardando sincronização automática com o servidor...")

# ==========================================
# ABA 5: DEBUG DA API
# ==========================================
with tab5:
    st.header("🛠️ Inspecionar JSON Bruto")
    if st.session_state.dados_campanha:
        st.code(json.dumps(st.session_state.dados_campanha, indent=4), language="json")
    else:
        st.info("A API ainda não foi carregada.")
