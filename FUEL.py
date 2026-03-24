import streamlit as st
import json
import math
import requests
import time
from deep_translator import GoogleTranslator

# ==========================================
# 0. INICIALIZAÇÃO DA MEMÓRIA (SESSION STATE)
# ==========================================
if 'vento_vel_cb' not in st.session_state: st.session_state.vento_vel_cb = 5.0
if 'vento_dir_cb' not in st.session_state: st.session_state.vento_dir_cb = 45.0
if 'temp_cb' not in st.session_state: st.session_state.temp_cb = 15.0
if 'nuvens_hoje_cb' not in st.session_state: st.session_state.nuvens_hoje_cb = "Desconhecido"

if 'vento_vel_amanha_cb' not in st.session_state: st.session_state.vento_vel_amanha_cb = 5.0
if 'vento_dir_amanha_cb' not in st.session_state: st.session_state.vento_dir_amanha_cb = 45.0
if 'temp_amanha_cb' not in st.session_state: st.session_state.temp_amanha_cb = 15.0
if 'nuvens_amanha_cb' not in st.session_state: st.session_state.nuvens_amanha_cb = "Desconhecido"

if 'status_cb' not in st.session_state: st.session_state.status_cb = "A aguardar sincronização..."
if 'dados_campanha' not in st.session_state: st.session_state.dados_campanha = None

# Memória Híbrida do NavLog
if 'navlog_manual' not in st.session_state:
    st.session_state.navlog_manual = [{"Perna": "Base ➔ Alvo", "Distância (km)": 50.0, "Rumo (TC)": 90.0}]
if 'vel_calc' not in st.session_state: st.session_state.vel_calc = 320.0
if 'dist_calc' not in st.session_state: st.session_state.dist_calc = 250.0
if 'usar_dados_importados' not in st.session_state: st.session_state.usar_dados_importados = False
if 'last_file_hash' not in st.session_state: st.session_state.last_file_hash = None


# ==========================================
# 1. FUNÇÕES DA API E TRADUÇÃO
# ==========================================
@st.cache_data(ttl=3600)
def traduzir_texto(texto):
    if not texto or texto.strip() == "":
        return ""
    try:
        tradutor = GoogleTranslator(source='en', target='pt')
        return tradutor.translate(texto)
    except Exception:
        return texto 

def fetch_combatbox_data():
    try:
        api_url = "https://campaign-data.combatbox.net/rhineland-campaign/rhineland-campaign-latest.json.aspx"
        response = requests.get(api_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=8)
        
        if response.status_code != 200:
            st.session_state.status_cb = f"❌ Erro HTTP {response.status_code}"
            return
            
        dados_json = response.json()
        st.session_state.dados_campanha = dados_json 
        
        weather_hoje = dados_json.get("Weather", {})
        wind_hoje = weather_hoje.get("WindAtGroundLevel", {})
        st.session_state.temp_cb = float(weather_hoje.get("Temperature", 15.0))
        st.session_state.vento_vel_cb = float(wind_hoje.get("Speed", 5.0))
        st.session_state.vento_dir_cb = float(wind_hoje.get("Bearing", 45.0))
        st.session_state.nuvens_hoje_cb = weather_hoje.get("CloudDescription", "N/D")

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
    "He-111 H-16": {
        "peso_base_sem_combustivel": 9300, "peso_max": 14000, "consumo_l_min": 10.2, "vel_cruzeiro_padrao": 330, "tanque_max_l": 3450,
        "armamento_fixo": "4x 7.92mm | 1x 20mm | 1x 13mm",
        "modificacoes": {"Padrão": 0},
        "presets_bombas": {"Vazio": 0, "16x SC 50": 800, "32x SC 50": 1600, "4x SC 250": 1000, "8x SC 250": 2000, "2x SC 500": 1000, "2x SC 1800": 3560, "1x SC 2500": 2400}
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
# 3. INTERFACE E BARRA LATERAL
# ==========================================
st.set_page_config(page_title="Painel Tático - Combat Box", layout="wide")
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
tab1, tab2, tab3, tab4 = st.tabs(["📊 Hangar", "🎯 Lotfe 7", "🧮 E6B & NavLog", "🌐 Inteligência Global"])
# ==========================================
# ABA 1: HANGAR
# ==========================================
with tab1:
    arquivo_plano = st.file_uploader("📥 Importar .json do Mission Planner (Opcional)", type=["json"])
    
    # Motor de Leitura de JSON com proteção contra sobrescrita contínua
    if arquivo_plano is not None:
        file_content = arquivo_plano.getvalue()
        current_hash = hash(file_content)
        
        # Só atualiza a tabela do NavLog no exato momento em que o ficheiro é enviado
        if st.session_state.last_file_hash != current_hash:
            st.session_state.last_file_hash = current_hash
            try:
                dados_plano = json.loads(file_content)
                if "routes" in dados_plano and len(dados_plano["routes"]) > 0 and "latLngs" in dados_plano["routes"][0]:
                    rota = dados_plano["routes"][0]
                    coords = rota["latLngs"]
                    
                    dist_total = 0.0
                    navlog_temp = []
                    for i in range(len(coords)-1):
                        dx = coords[i+1]['lng'] - coords[i]['lng']
                        dy = coords[i+1]['lat'] - coords[i]['lat']
                        dist = math.hypot(dx, dy) * 3.0
                        dist_total += dist
                        tc_deg = (math.degrees(math.atan2(dx, -dy)) + 360) % 360
                        navlog_temp.append({"Perna": f"WP{i} ➔ WP{i+1}", "Distância (km)": round(dist, 1), "Rumo (TC)": round(tc_deg, 0)})
                    
                    st.session_state.navlog_manual = navlog_temp
                    st.session_state.dist_calc = dist_total
                    st.session_state.vel_calc = float(rota.get("speed", 320.0))
                    st.session_state.usar_dados_importados = True
                    
                    st.success("✅ Rota tática importada! O NavLog (Aba 3) foi preenchido automaticamente.")
            except:
                st.error("Erro ao ler JSON.")

    col_esq, col_dir = st.columns(2)
    with col_esq:
        aviao = db_avioes[st.selectbox("Aeronave", list(db_avioes.keys()))]
        distancia_km = st.number_input("Distância (km)", value=float(st.session_state.dist_calc), disabled=st.session_state.usar_dados_importados)
        velocidade_estimada = st.number_input("Velocidade (km/h)", value=float(st.session_state.vel_calc), disabled=st.session_state.usar_dados_importados)
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
# ABA 2: LOTFE 7
# ==========================================
with tab2:
    b1, b2 = st.columns(2)
    with b1:
        altitude = st.number_input("Altitude (m)", value=3000)
        ias = st.number_input("IAS (km/h)", value=280)
        proa_alvo = st.number_input("Proa (°)", value=90)
    with b2:
        vel_vento = st.number_input("Vel. Vento (m/s)", value=float(st.session_state.vento_vel_cb))
        dir_vento = st.number_input("Dir. Vento (°)", value=float(st.session_state.vento_dir_cb))

    tas_ms = (ias * (1 + (altitude / 1000) * 0.05)) / 3.6
    ang_vento_rad = math.radians(dir_vento - proa_alvo)
    try: deriva_graus = math.degrees(math.asin(max(-1.0, min(1.0, (vel_vento * math.sin(ang_vento_rad)) / tas_ms))))
    except: deriva_graus = 0.0
    gs_kmh = ((tas_ms * math.cos(math.radians(deriva_graus))) - (vel_vento * math.cos(ang_vento_rad))) * 3.6
    
    st.metric("Insira na Lotfe: Velocidade Solo (GS)", f"{gs_kmh:.0f} km/h")
    st.metric("Insira na Lotfe: Ângulo de Deriva", f"{abs(deriva_graus):.1f}° {'Direita' if deriva_graus > 0 else 'Esquerda'}")

# ==========================================
# ABA 3: E6B & NAVLOG HÍBRIDO
# ==========================================
with tab3:
    st.header("🗺️ Centro de Navegação")
    st.markdown("O **NavLog** (tabela) regista a rota. O **E6B** (motor) compensa o vento automaticamente.")
    
    c_tas, c_dir, c_vel = st.columns(3)
    with c_tas:
        nav_tas = st.number_input("Sua TAS esperada (km/h)", value=float(st.session_state.vel_calc), step=10.0)
    with c_dir:
        nav_w_dir = st.number_input("Vento vindo DE (°)", value=float(st.session_state.vento_dir_cb), key="nav_dir_e6b")
    with c_vel:
        nav_w_spd = st.number_input("Vel. Vento (km/h)", value=float(st.session_state.vento_vel_cb * 3.6), step=5.0, key="nav_spd_e6b")

    # --- O DOCUMENTO (NAVLOG) ---
    st.subheader("📝 Navigation Log (Diário de Rota)")
    navlog_editado = st.data_editor(
        st.session_state.navlog_manual, 
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Perna": st.column_config.TextColumn("Nome da Perna"),
            "Distância (km)": st.column_config.NumberColumn("Distância (km)", min_value=0.1, format="%.1f"),
            "Rumo (TC)": st.column_config.NumberColumn("Rumo Mapa (TC °)", min_value=0.0, max_value=360.0, format="%.0f")
        }
    )
    st.session_state.navlog_manual = navlog_editado
    
    if len(navlog_editado) > 0:
        resultados_finais = []
        for linha in navlog_editado:
            try:
                dist = float(linha.get("Distância (km)", 0.0))
                tc_deg = float(linha.get("Rumo (TC)", 0.0))
            except:
                dist, tc_deg = 0.0, 0.0
                
            nome_perna = linha.get("Perna", "N/D")
            
            if dist > 0:
                wa_rad = math.radians(nav_w_dir - tc_deg)
                try:
                    sin_wca = max(-1.0, min(1.0, (nav_w_spd * math.sin(wa_rad)) / nav_tas))
                    wca_deg = math.degrees(math.asin(sin_wca))
                except: wca_deg = 0.0

                th_deg = (tc_deg + wca_deg + 360) % 360
                gs_leg = (nav_tas * math.cos(math.radians(wca_deg))) - (nav_w_spd * math.cos(wa_rad))
                gs_leg = max(1.0, gs_leg)
                
                tempo_min = (dist / gs_leg) * 60
                
                resultados_finais.append({
                    "📍 Perna": nome_perna,
                    "🗺️ Rumo Mapa": f"{tc_deg:.0f}°",
                    "🧭 Voar PROA (TH)": f"{th_deg:.0f}°",
                    "💨 Vel. Solo (GS)": f"{gs_leg:.0f} km/h",
                    "⏱️ Tempo Voo": f"{tempo_min:.1f} min"
                })
        
        if resultados_finais:
            st.table(resultados_finais)

    st.divider()

    # --- A FERRAMENTA (E6B) ---
    st.subheader("🧮 Computador E6B (Cálculos de Bordo)")
    col_tsd, col_conv = st.columns(2)
    
    with col_tsd:
        st.markdown("**⏱️ Tempo, Velocidade, Distância (TSD)**")
        modo_tsd = st.radio("Calcular:", ["Tempo", "Distância", "Velocidade (GS)"], horizontal=True)
        if modo_tsd == "Tempo":
            d_in = st.number_input("Distância (km)", value=50.0, key="d_t")
            v_in = st.number_input("Velocidade (km/h)", value=300.0, key="v_t")
            if v_in > 0: st.info(f"**Resultado:** {(d_in/v_in)*60:.1f} minutos")
        elif modo_tsd == "Distância":
            t_in = st.number_input("Tempo (min)", value=10.0, key="t_d")
            v_in = st.number_input("Velocidade (km/h)", value=300.0, key="v_d")
            st.info(f"**Resultado:** {v_in*(t_in/60):.1f} km")
        else:
            d_in = st.number_input("Distância (km)", value=50.0, key="d_v")
            t_in = st.number_input("Tempo (min)", value=10.0, key="t_v")
            if t_in > 0: st.info(f"**Resultado:** {d_in/(t_in/60):.0f} km/h")
            
    with col_conv:
        st.markdown("**🔄 Conversões Imperiais**")
        cat_conv = st.selectbox("Unidade:", ["Velocidade (km/h ↔ mph)", "Altitude (metros ↔ pés)"])
        val_conv = st.number_input("Valor:", value=1000.0 if "Altitude" in cat_conv else 300.0)
        
        if "Velocidade" in cat_conv:
            st.warning(f"**{val_conv} km/h** = {val_conv / 1.60934:.0f} mph")
            st.warning(f"**{val_conv} mph** = {val_conv * 1.60934:.0f} km/h")
        else:
            st.warning(f"**{val_conv} metros** = {val_conv * 3.28084:.0f} pés")
            st.warning(f"**{val_conv} pés** = {val_conv / 3.28084:.0f} metros")
            
with col_b:
            st.subheader("🛫 Infraestrutura da Base")
            bases = dados.get('Airfields', [])
            if bases:
                base_sel = st.selectbox("Inspecionar Base:", [b.get('Name', 'Base') for b in bases])
                dados_base = next((b for b in bases if b.get('Name') == base_sel), None)
                
                if dados_base:
                    # --- NOVO: SISTEMA DE ALERTA DE ATAQUE ---
                    # Tenta ler as chaves mais comuns de ataque no servidor
                    sob_ataque = dados_base.get('UnderAttack', False)
                    if not sob_ataque: # Fallback caso a chave tenha outro nome
                        sob_ataque = dados_base.get('IsUnderAttack', False)
                        
                    if sob_ataque:
                        st.error("🚨 **ALERTA MÁXIMO: BASE SOB ATAQUE!** 🚨\n\nRisco extremo de 'Vulching' (ataque na pista).")
                    else:
                        st.success("✅ **Status: Base Segura**")
                    
                    st.divider()
                    
                    # 1. Extração dos Dados Físicos da Base
                    supply = dados_base.get('SupplyLevel', 0)
                    bearing = dados_base.get('RunwayBearing', 0)
                    is_concrete = dados_base.get('RunwayIsConcrete', False)
                    
                    # 2. Cálculos e Formatação
                    bearing_opp = (bearing + 180) % 360
                    tipo_pista = "🛣️ Concreto / Asfalto" if is_concrete else "🌱 Grama / Terra"
                    
                    # 3. Desenho da UI
                    st.caption("Detalhes da Pista")
                    st.write(f"**Proa (Alinhamento):** {bearing:03.0f}° / {bearing_opp:03.0f}°")
                    st.write(f"**Superfície:** {tipo_pista}")
                    
                    supply_val = max(0, min(100, int(supply)))
                    st.progress(supply_val / 100.0, text=f"📦 Nível de Suprimentos: {supply_val}%")
                    
                    st.divider()
                    
                    # 4. Inventário do Hangar
                    st.caption("Aeronaves no Hangar")
                    avioes_base = dados_base.get('AvailableAirframes', [])
                    if avioes_base:
                        for av in avioes_base:
                            st.write(f"- {av.get('Type', 'Aeronave')}: **{av.get('NumberAvailable', 0)}** unid.")
                    else:
                        st.write("Sem aeronaves listadas.")
    else:
        st.info("Aguardando sincronização automática com o servidor...")
