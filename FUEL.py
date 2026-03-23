import streamlit as st
import json
import math
import requests
import time 

# ==========================================
# 0. INICIALIZAÇÃO DA MEMÓRIA (SESSION STATE)
# ==========================================
if 'vento_vel_cb' not in st.session_state: st.session_state.vento_vel_cb = 5.0
if 'vento_dir_cb' not in st.session_state: st.session_state.vento_dir_cb = 45.0
if 'temp_cb' not in st.session_state: st.session_state.temp_cb = 15.0
if 'status_cb' not in st.session_state: st.session_state.status_cb = "A aguardar sincronização com o servidor..."
if 'dados_campanha' not in st.session_state: st.session_state.dados_campanha = None

# ==========================================
# 1. FUNÇÃO DA API JSON (EXTRAÇÃO NATIVA)
# ==========================================
def fetch_combatbox_data():
    """Integração direta baseada no mapeamento exato do banco de dados"""
    try:
        api_url = "https://campaign-data.combatbox.net/rhineland-campaign/rhineland-campaign-latest.json.aspx"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(api_url, headers=headers, timeout=8)
        
        if response.status_code != 200:
            st.session_state.status_cb = f"❌ Erro HTTP {response.status_code}"
            return
            
        dados_json = response.json()
        st.session_state.dados_campanha = dados_json 
        
        # Navegação exata pela árvore do JSON que o Gustavo mapeou!
        weather = dados_json.get("Weather", {})
        wind = weather.get("WindAtGroundLevel", {})
        
        if weather and wind:
            st.session_state.temp_cb = float(weather.get("Temperature", 15.0))
            st.session_state.vento_vel_cb = float(wind.get("Speed", 5.0))
            st.session_state.vento_dir_cb = float(wind.get("Bearing", 45.0))
            st.session_state.status_cb = "✅ API Sincronizada! Telemetria Tática AO VIVO."
        else:
            st.session_state.status_cb = "⚠️ JSON lido, mas a aba 'Weather' não foi encontrada."
            
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
# 3. INTERFACE E BARRA LATERAL
# ==========================================
st.set_page_config(page_title="Painel Tático", layout="wide")
st.markdown("""<style>.stApp { background-color: #0E1117; color: #FAFAFA; }</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.header("📡 Comando e Controlo")
    if st.button("🔄 Puxar Dados do Servidor", use_container_width=True):
        fetch_combatbox_data()
        
    st.info(st.session_state.status_cb)
    st.divider()
    st.metric("Vento Dominante", f"{st.session_state.vento_vel_cb} m/s")
    st.metric("Direção do Vento", f"{st.session_state.vento_dir_cb}°")
    st.metric("Temperatura Local", f"{st.session_state.temp_cb} °C")

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
# 3. INTERFACE E BARRA LATERAL (AO VIVO)
# ==========================================
st.set_page_config(page_title="Painel Tático", layout="wide")
st.markdown("""<style>.stApp { background-color: #0E1117; color: #FAFAFA; }</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.header("📡 Comando e Controlo")
    st.markdown("Telemetria em tempo real ligada ao Combat Box.")
    
    # Este "decorador" diz ao Python para rodar esta função sozinho a cada 60 segundos!
    @st.fragment(run_every="60s")
    def telemetria_automatica():
        # Executa a nossa função de API silenciosamente no fundo
        fetch_combatbox_data()
        
        # Desenha os mostradores que vão piscar sozinhos a cada minuto
        st.info(st.session_state.status_cb)
        st.divider()
        st.metric("Vento Dominante", f"{st.session_state.vento_vel_cb} m/s")
        st.metric("Direção do Vento", f"{st.session_state.vento_dir_cb}°")
        st.metric("Temperatura Local", f"{st.session_state.temp_cb} °C")
        
        # Mostra a hora exata da última "batida" no servidor para você saber que está vivo
        st.caption(f"⏱️ Última sincronização: {time.strftime('%H:%M:%S')}")

    # Chamamos a função para ela começar o loop infinito
    telemetria_automatica()

# ==========================================
# ABA 4: INTELIGÊNCIA GLOBAL (REESCRITA PARA O JSON REAL)
# ==========================================
with tab4:
    st.header("🌐 Inteligência Tática e Logística")
    if st.session_state.dados_campanha:
        dados = st.session_state.dados_campanha
        
        col_w, col_t = st.columns([1, 2])
        
        with col_w:
            st.subheader("⛅ Clima e Frontline")
            st.info(f"O Céu amanhã: {dados.get('WeatherTomorrow', {}).get('CloudDescription', 'Desconhecido')}")
            st.caption(dados.get('CurrentDayStateDescription', ''))
                
        with col_t:
            st.subheader("🎯 Objetivos Terrestres")
            objetivos = dados.get('Objectives', [])
            objetivos_ativos = [o for o in objetivos if o.get('ActiveToday') == True]
            for obj in objetivos_ativos[:5]:
                st.warning(f"**{obj.get('Name', 'Alvo')}** ({obj.get('Type', 'Instalação')}) - Zona: {obj.get('Coalition', 'N/D')}")
                
        st.divider()
        c_bases, c_ops = st.columns(2)
        
        with c_bases:
            st.subheader("🛫 Logística de Base (Disponibilidade)")
            bases = dados.get('Airfields', [])
            if bases:
                base_sel = st.selectbox("Inspecionar Estoque:", [b.get('Name', 'Base') for b in bases])
                dados_base = next((b for b in bases if b.get('Name') == base_sel), None)
                if dados_base:
                    avioes_base = dados_base.get('AvailableAirframes', [])
                    if avioes_base:
                        for av in avioes_base:
                            st.write(f"- {av.get('ColloquialName', av.get('Type', 'Aeronave'))}: **{av.get('NumberAvailable', 0)}** unidades")
                    else:
                        st.write("Sem aeronaves listadas.")
                        
        with c_ops:
            st.subheader("🪂 Operações de Paraquedistas")
            paras = dados.get('ParatrooperOps', [])
            if paras:
                for op in paras:
                    st.success(f"Jogador: {op.get('Player', 'Piloto')} | Lançados: {op.get('DroppedInDz', 0)}")
            else:
                st.caption("Nenhuma operação de salto registada recentemente.")
    else:
        st.info("Clique em 'Puxar Dados do Servidor' na barra lateral para carregar a Inteligência.")
