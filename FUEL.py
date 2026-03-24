import streamlit as st
import json
import math
import requests
import time
import pandas as pd
from deep_translator import GoogleTranslator

# ==========================================
# 0. INICIALIZAÇÃO DA MEMÓRIA (SESSION STATE)
# ==========================================
# Variáveis de Meteorologia
if 'vento_vel_cb' not in st.session_state: st.session_state.vento_vel_cb = 5.0
if 'vento_dir_cb' not in st.session_state: st.session_state.vento_dir_cb = 45.0
if 'temp_cb' not in st.session_state: st.session_state.temp_cb = 15.0
if 'status_cb' not in st.session_state: st.session_state.status_cb = "A aguardar sincronização..."
if 'dados_campanha' not in st.session_state: st.session_state.dados_campanha = None

# Memória do NavLog e FMC (O QUE ESTAVA A FALTAR)
if 'navlog_manual' not in st.session_state:
    st.session_state.navlog_manual = [{"Perna": "Base ➔ Alvo", "Distância (km)": 50.0, "Rumo (TC)": 90.0}]

if 'index_perna_ativa' not in st.session_state: 
    st.session_state.index_perna_ativa = 0

if 'cronometro_rodando' not in st.session_state: 
    st.session_state.cronometro_rodando = False

if 'tempo_inicio_perna' not in st.session_state: 
    st.session_state.tempo_inicio_perna = None

# Controlo de Ficheiros e Cálculos
if 'vel_calc' not in st.session_state: st.session_state.vel_calc = 320.0
if 'dist_calc' not in st.session_state: st.session_state.dist_calc = 250.0
if 'last_file_hash' not in st.session_state: st.session_state.last_file_hash = None

if 'tempo_pausado_acumulado' not in st.session_state: 
    st.session_state.tempo_pausado_acumulado = 0.0

# --- Inicialização de variáveis de tempo ---
if 'tempo_inicio_missao_absoluto' not in st.session_state:
    st.session_state.tempo_inicio_missao_absoluto = None

if 'cronometro_rodando' not in st.session_state:
    st.session_state.cronometro_rodando = False

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
        
        # --- AJUSTE DE CONVENÇÃO: HOJE ---
        weather_hoje = dados_json.get("Weather", {})
        wind_hoje = weather_hoje.get("WindAtGroundLevel", {})
        st.session_state.temp_cb = float(weather_hoje.get("Temperature", 15.0))
        st.session_state.vento_vel_cb = float(wind_hoje.get("Speed", 5.0))
        
        # Inversão de 180 graus para converter "Para Onde" em "De Onde"
        bearing_bruto = float(wind_hoje.get("Bearing", 45.0))
        st.session_state.vento_dir_cb = (bearing_bruto + 180) % 360

        # --- AJUSTE DE CONVENÇÃO: AMANHÃ ---
        weather_amanha = dados_json.get("WeatherTomorrow", {})
        wind_amanha = weather_amanha.get("WindAtGroundLevel", {})
        st.session_state.temp_amanha_cb = float(weather_amanha.get("Temperature", 15.0))
        st.session_state.vento_vel_amanha_cb = float(wind_amanha.get("Speed", 5.0))
        
        bearing_amanha_bruto = float(wind_amanha.get("Bearing", 45.0))
        st.session_state.vento_dir_amanha_cb = (bearing_amanha_bruto + 180) % 360
        
        st.session_state.status_cb = "✅ API Sincronizada!"
            
    except Exception as e:
        st.session_state.status_cb = f"❌ Erro de Ligação: {e}"


# ==========================================
# 2.1 BASE DE DADOS DEFINITIVA (ALTITUDES)
# ==========================================
db_altitudes_tecnico = {
    "Aachen": 190, "Achmer": 54, "Bad Lippspringe": 140, "Breitscheid": 558,
    "Chievres": 59, "Coesfeld-Lette": 80, "Deelen": 48, "Deurne": 12,
    "Diest": 27, "Dortmund": 129, "Eudenbach": 360, "Florennes": 285,
    "Gilze-Rijen": 15, "Greven": 48, "Guetersloh": 80, "Kirchhellen": 67,
    "Liege": 201, "Limburg": 31, "Melsbroek": 56, "Nivelles": 103,
    "Petit Brogel": 61, "Plantluenne": 35, "Quackenbrueck": 24, "Schiphol": 0,
    "Sint-Denijs-Westrem": 8, "Soesterberg": 20, "Stoermede": 90,
    "Strassfeld": 161, "Twente": 35, "Venlo": 30, "Volkel": 14, "Woensdrecht": 19
}

# ==========================================
# 2. BASE DE DADOS COMPLETA: AERONAVES (C4ISR)
# ==========================================
db_avioes = {
    "He-111 H-16": {
        "peso_base_sem_combustivel": 9300, 
        "peso_max": 14000, 
        "consumo_l_min": 10.2, 
        "vel_cruzeiro_padrao": 330, 
        "tanque_max_l": 3450,
        "climb_rate_default": 2.5, 
        "descent_rate_default": 4.0,
        "armamento_fixo": "4x 7.92mm MG-81J | 1x 20mm MG-FF | 1x 13mm MG-131",
        "modificacoes": {
            "Padrão": 0,
            "Remover Blindagem": -115,
            "Tanque Adicional": 150
        },
        "presets_bombas": {
            "Vazio": 0, 
            "1x SC 2500 (Max)": 2400, 
            "2x SC 1800 (Satan)": 3560, 
            "2x SC 1000 (Hermann)": 2180, 
            "8x SC 250": 2000, 
            "32x SC 50": 1600
        }
    },
    "He-111 H-6": {
        "peso_base_sem_combustivel": 9500, 
        "peso_max": 14000, 
        "consumo_l_min": 10.5, 
        "vel_cruzeiro_padrao": 320, 
        "tanque_max_l": 3450,
        "climb_rate_default": 2.5, 
        "descent_rate_default": 4.0,
        "armamento_fixo": "6x 7.92mm MG-15",
        "modificacoes": {
            "Padrão": 0, 
            "Torre Frontal (20mm)": 46, 
            "Torre Ventral": 147, 
            "Kit Anti-Navio": 193
        },
        "presets_bombas": {
            "Vazio": 0, 
            "2x SC 1000": 2180, 
            "1x SC 1800": 1780, 
            "4x SC 250": 1000, 
            "16x SC 50": 800
        }
    },
    "Ju-52/3M": {
        "peso_base_sem_combustivel": 7500, 
        "peso_max": 11000, 
        "consumo_l_min": 12.0, 
        "vel_cruzeiro_padrao": 240, 
        "tanque_max_l": 2450,   
        "climb_rate_default": 2.0, 
        "descent_rate_default": 3.0,
        "armamento_fixo": "1x 13mm MG-131 (Dorsal)",
        "modificacoes": {
            "Padrão": 0, 
            "Paraquedistas (12 homens)": 1200, 
            "Carga Interna Tática": 2300, 
            "Rodas de Inverno": 45
        },
        "presets_bombas": {
            "Vazio": 0, 
            "10x MAB 250 (Containers)": 2550,
            "12x SC 50": 600
        }
    },
    "Ju-88 A-4": {
        "peso_base_sem_combustivel": 8600, 
        "peso_max": 14000, 
        "consumo_l_min": 10.0, 
        "vel_cruzeiro_padrao": 370, 
        "tanque_max_l": 1680,   
        "climb_rate_default": 3.5, 
        "descent_rate_default": 5.0,
        "armamento_fixo": "1x 13mm MG-131 | 3x 7.92mm MG-81J",
        "modificacoes": {
            "Padrão": 0, 
            "Sem Dive Brakes": -60, 
            "Sem Gôndola Inferior": -123,
            "Câmera de Reconhecimento": 25
        },
        "presets_bombas": {
            "Vazio": 0, 
            "4x SC 500": 2000, 
            "10x SC 50 (Interno)": 500, 
            "28x SC 50 (Full Load)": 1400,
            "2x SC 1000": 2180
        }
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
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Hangar", "🎯 Lotfe 7", "🧮 NavLog & E6B", "🚀 FMC (Ativo)", "🌐 Inteligência"])

# ==========================================
# ABA 1: HANGAR (LOGÍSTICA E PREPARAÇÃO)
# ==========================================
with tab1:
    st.header("🛠️ Configuração de Carga e Rota")
    
    # --- Seção de Importação ---
    col_f, col_clear = st.columns([3, 1])
    with col_f: 
        arquivo_plano = st.file_uploader("📥 Importar Rota (.json)", type=["json"])
        
        if arquivo_plano is not None:
            file_content = arquivo_plano.getvalue()
            current_hash = hash(file_content)
            
            if st.session_state.get('last_file_hash') != current_hash:
                st.session_state.last_file_hash = current_hash
                try:
                    dados_plano = json.loads(file_content)
                    if "routes" in dados_plano: 
                        rota = dados_plano["routes"][0]
                        coords = rota["latLngs"]
                        navlog_temp = []
                        dist_total = 0.0
                        for i in range(len(coords)-1):
                            dx, dy = coords[i+1]['lng'] - coords[i]['lng'], coords[i+1]['lat'] - coords[i]['lat']
                            d_perna = math.hypot(dx, dy) * 3.0 
                            dist_total += d_perna
                            tc_deg = (math.degrees(math.atan2(dx, -dy)) + 360) % 360
                            navlog_temp.append({"Perna": f"WP{i}➔WP{i+1}", "Distância (km)": round(d_perna, 1), "Rumo (TC)": round(tc_deg, 0)})
                        st.session_state.navlog_manual = navlog_temp
                        st.session_state.dist_calc = dist_total
                    else: 
                        st.session_state.navlog_manual = dados_plano
                        st.session_state.dist_calc = sum(item.get("Distância (km)", 0) for item in dados_plano)
                    st.success("✅ Rota carregada com sucesso!")
                except: st.error("Erro ao processar o arquivo JSON.")
            
    with col_clear:
        if st.button("🗑️ Reset Rota", use_container_width=True): 
            st.session_state.navlog_manual = []
            st.session_state.dist_calc = 100.0
            st.rerun()

    st.divider()
    
    # --- Seleção de Avião e Pesos (Chaves Atualizadas) ---
    c1, c2 = st.columns(2)
    with c1:
        av_nome = st.selectbox("Selecione a Aeronave", list(db_avioes.keys()))
        av = db_avioes[av_nome]
        
        # Uso das chaves longas conforme sua base de dados
        missao_dist = st.number_input("Distância da Missão (km)", value=float(st.session_state.get('dist_calc', 100.0)))
        missao_vel = st.number_input("Velocidade de Cruzeiro (km/h)", value=float(av['vel_cruzeiro_padrao']))
        margem_seg = st.slider("Reserva de Combustível (%)", 0, 100, 30)
    
    with c2:
        mod_sel = st.selectbox("Modificações", list(av['modificacoes'].keys()))
        bomb_sel = st.selectbox("Carga de Bombas", list(av['presets_bombas'].keys()))
        st.caption(f"🛡️ Armamento Fixo: {av.get('armamento_fixo', 'Não listado')}")
        
    # --- Cálculos Logísticos ---
    tempo_estimado = (missao_dist / missao_vel) * 60
    # Chave consumo_l_min
    comb_l = tempo_estimado * av['consumo_l_min'] * (1 + (margem_seg / 100))
    # Chave peso_base_sem_combustivel
    peso_total = av['peso_base_sem_combustivel'] + av['modificacoes'][mod_sel] + av['presets_bombas'][bomb_sel] + (comb_l * 0.72)
    
    st.divider()
    col_res1, col_res2 = st.columns(2)
    with col_res1:
        if peso_total <= av['peso_max']:
            st.success(f"⚖️ Peso Total: **{peso_total:.0f} kg** / {av['peso_max']} kg")
        else:
            st.error(f"⚠️ SOBRECARGA: **{peso_total:.0f} kg** / {av['peso_max']} kg")
    with col_res2:
        st.info(f"⛽ Combustível: **{comb_l:.0f} Litros**")
        st.caption(f"Capacidade Máxima: {av['tanque_max_l']} L")
        
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


# ==========================================
# ABA 4: FMC (LISTA DEFINITIVA DO DB)
# ==========================================
with tab4:
    st.header("🚀 Flight Management Computer")
    
    # 1. VALIDAÇÃO DE ROTA
    if not st.session_state.get('navlog_manual'):
        st.info("⚠️ Configure uma rota na Aba 1 ou Aba 3 para ativar o FMC.")
    else:
        # 2. FONTE DE DADOS DEFINITIVA (SEU DB)
        # Ordenamos a lista alfabeticamente para facilitar a busca
        lista_aerodromos_db = sorted(list(db_altitudes_tecnico.keys()))

        # 3. INTERFACE DE SELEÇÃO
        with st.expander("🌍 Configuração de Aeródromos (DB Interno)", expanded=True):
            col_dep, col_arr = st.columns(2)
            
            with col_dep:
                # Agora o menu usa estritamente a sua lista do DB
                base_dep = st.selectbox("Decolagem de:", lista_aerodromos_db, key="fmc_dep_estatico")
                alt_dep = db_altitudes_tecnico[base_dep] # Acesso direto, sem fallback necessário
                st.write(f"**Altitude Base:** {alt_dep}m")
                
            with col_arr:
                base_arr = st.selectbox("Destino Final:", lista_aerodromos_db, key="fmc_arr_estatico")
                alt_arr = db_altitudes_tecnico[base_arr]
                st.write(f"**Altitude Alvo:** {alt_arr}m")

        # 4. PERFORMANCE VERTICAL (VNAV)
        av_nome = st.session_state.get('av_nome_selecionado', "He-111 H-16")
        av = db_avioes.get(av_nome, {})

        with st.expander("📈 Perfil de Voo", expanded=True):
            v1, v2, v3, v4 = st.columns(4)
            with v1: alt_cruzeiro = st.number_input("Cruzeiro (m)", value=4000, step=500)
            with v2: climb_rate = st.number_input("Subida (m/s)", value=float(av.get('climb_rate_default', 2.5)))
            with v3: descent_rate = st.number_input("Descida (m/s)", value=float(av.get('descent_rate_default', 4.0)))
            with v4: alt_pista = st.number_input("Alt. Aeródromo (m)", value=alt_arr)

        # --- CÁLCULO DE ROTA ---
        nav_tas = float(st.session_state.get('vel_calc', 320))
        w_dir = float(st.session_state.get('vento_dir_cb', 45.0))
        w_spd = float(st.session_state.get('vento_vel_cb', 5.0) * 3.6)
        
        pernas_fmc = []
        dist_acum = 0
        for idx, linha in enumerate(st.session_state.navlog_manual):
            try:
                dist = float(linha.get("Distância (km)", 0.0))
                tc = float(linha.get("Rumo (TC)", 0.0))
                wa_rad = math.radians(w_dir - tc)
                sin_wca = max(-1.0, min(1.0, (w_spd * math.sin(wa_rad)) / nav_tas))
                wca = math.degrees(math.asin(sin_wca))
                th = (tc + wca + 360) % 360
                gs = max(1.0, (nav_tas * math.cos(math.radians(wca))) - (w_spd * math.cos(wa_rad)))
                tempo = (dist / gs) * 3600
                dist_acum += dist
                pernas_fmc.append({"id": idx, "nome": linha.get("Perna", f"WP{idx}"), "proa": th, "tempo": tempo, "dist_total": dist_acum})
            except: continue

        # --- GRÁFICO VNAV ---
        if pernas_fmc:
            total_km = pernas_fmc[-1]['dist_total']
            dist_climb = ((alt_cruzeiro - alt_dep) / climb_rate) * (nav_tas / 3600)
            dist_descent = ((alt_cruzeiro - alt_arr) / descent_rate) * (nav_tas / 3600)
            
            df_vnav = pd.DataFrame({
                "Distância (km)": [0, dist_climb, max(dist_climb, total_km - dist_descent), total_km],
                "Altitude (m)": [alt_dep, alt_cruzeiro, alt_cruzeiro, alt_arr]
            })
            st.area_chart(df_vnav.set_index("Distância (km)"))

        st.divider()

        # --- HUD DE EXECUÇÃO E ALERTA DE COMBUSTÍVEL ---
        @st.fragment(run_every="1s")
        def fmc_hud_final():
            idx = st.session_state.index_perna_ativa
            if idx < len(pernas_fmc):
                p = pernas_fmc[idx]
                h1, h2, h3 = st.columns([2, 1, 1])
                
                with h1:
                    st.subheader(f"📍 Perna: {p['nome']}")
                    st.markdown(f"## 🧭 PROA: {p['proa']:.0f}°")
                
                with h2:
                    if st.session_state.cronometro_rodando:
                        passado = time.time() - st.session_state.tempo_inicio_perna
                        restante = max(0, p['tempo'] - passado)

# --- HUD DE EXECUÇÃO E ALERTA DE COMBUSTÍVEL ---
@st.fragment(run_every="1s")
def fmc_hud_final():
    idx = st.session_state.index_perna_ativa
    
    if idx < len(pernas_fmc):
        p = pernas_fmc[idx]
        h1, h2, h3 = st.columns([2, 1, 1])
        
        with h1:
            st.subheader(f"📍 Perna: {p['nome']}")
            st.markdown(f"## 🧭 PROA: {p['proa']:.0f}°")
        
        with h2:
            if st.session_state.cronometro_rodando:
                passado = time.time() - st.session_state.tempo_inicio_perna
                restante = max(0, p['tempo'] - passado)
                m, s = divmod(int(restante), 60)
                st.metric("Tempo WP", f"{m:02d}:{s:02d}")
            else:
                st.metric("Tempo WP", "--:--")

        # --- MONITOR VNAV EM TEMPO REAL ---
        distancia_tod_km = total_km - dist_descent 

        # SÓ CALCULA SE O CRONÔMETRO ESTIVER RODANDO E A VARIÁVEL EXISTIR
        if st.session_state.cronometro_rodando and st.session_state.tempo_inicio_missao_absoluto is not None:
            # 1. Tempo total desde a decolagem
            tempo_total_missao_seg = time.time() - st.session_state.tempo_inicio_missao_absoluto
            
            # 2. Distância total percorrida (estimada)
            # Nota: use nav_tas ou a GS calculada para a perna
            distancia_percorrida_total = (tempo_total_missao_seg / 3600) * nav_tas
            
            # 3. Distância para o ponto de descida (TOD)
            distancia_para_tod = distancia_tod_km - distancia_percorrida_total

            st.divider() 

            # ALERTAS DE ALTITUDE
            if 0 < distancia_para_tod <= 10:
                st.warning(f"📉 **PREPARAR DESCIDA:** TOD em {distancia_para_tod:.1f} km")
            elif distancia_para_tod <= 0:
                st.error(f"⬇️ **INICIAR PERDA DE ALTITUDE!** Passou {abs(distancia_para_tod):.1f} km")
            else:
                st.info(f"📊 Cruzeiro Estável. Próximo evento: Descida em {distancia_para_tod:.1f} km")

        # BOTÕES DE CONTROLE
        with h3:
            if not st.session_state.cronometro_rodando:
                if st.button("▶️ START", use_container_width=True):
                    st.session_state.cronometro_rodando = True
                    st.session_state.tempo_inicio_perna = time.time()
                    st.session_state.tempo_inicio_missao_absoluto = time.time() # Aqui ela é criada
                    st.rerun()
            else:
                if st.button("⏭️ NEXT", use_container_width=True):
                    st.session_state.index_perna_ativa += 1
                    st.session_state.tempo_inicio_perna = time.time()
                    st.rerun()
    else:
        st.success("🏁 Objetivo Atingido!")

fmc_hud_final()
# ==========================================
# ABA 5: INTELIGÊNCIA TÁTICA (C4ISR)
# ==========================================
with tab5:
    st.header("🌐 Inteligência Tática e Logística (C4ISR)")
    
    if not st.session_state.get('dados_campanha'):
        st.warning("📡 Aguardando sincronização com o servidor do Combat Box...")
    else:
        dados = st.session_state.dados_campanha
        airfields = dados.get('Airfields', [])
        
        # --- 1. BRIEFING DO COMANDO ---
        st.subheader("📜 Relatórios de Operações")
        texto_hoje = dados.get('CurrentDayStateDescription', '')
        if texto_hoje:
            st.info(f"**Briefing do Dia:**\n\n{traduzir_texto(texto_hoje)}")
        
        with st.expander("Ver Resumo das Operações Anteriores"):
            texto_ontem = dados.get('PreviousDaysEventsDescription', '')
            st.write(traduzir_texto(texto_ontem) if texto_ontem else "Sem registros adicionais.")
        
        st.divider()

        # --- 2. FUNÇÕES DE FILTRAGEM (TAG: ActiveToday) ---
        def filtrar_bases_por_atividade(lista, coalizao_alvo):
            resultado = []
            for b in lista:
                # Normalização de Coalizão
                b_coal = str(b.get('Coalition', '')).strip().lower()
                alvos = [c.lower() for c in coalizao_alvo]
                
                if b_coal in alvos:
                    # A TAG MESTRE ENCONTRADA POR VOCÊ:
                    is_active = b.get('ActiveToday')
                    
                    # Verificação robusta (funciona se for booleano ou string do JSON)
                    if str(is_active).lower() in ['true', '1']:
                        resultado.append(b)
            return resultado

        def render_hangar_logic(base):
            hangar = base.get('AvailableAirframes', [])
            if hangar:
                st.caption("Aeronaves em Hangar:")
                for av in hangar:
                    tipo = av.get('Type', 'Aeronave')
                    qtd = int(av.get('NumberAvailable', 0))
                    # REGRA TÉCNICA: -1 significa UNLIMITED
                    txt_qtd = "♾️ ILIMITADO" if qtd == -1 else f"{qtd} unid."
                    st.write(f"- {tipo}: **{txt_qtd}**")
            else:
                st.write("Sem estoque de aeronaves.")

        # --- 3. EXECUÇÃO ---
        aliados_ativos = filtrar_bases_por_atividade(airfields, ['Allies', 'Allied'])
        eixo_ativos = filtrar_bases_por_atividade(airfields, ['Axis'])

        # --- 4. EXIBIÇÃO DE AERÓDROMOS (COLUNAS) ---
        st.subheader(f"🛫 Bases Ativas na Missão: {len(aliados_ativos) + len(eixo_ativos)}")
        
        col_all_b, col_ax_b = st.columns(2)

        with col_all_b:
            st.markdown("### 🔵 Allies Active Bases")
            if not aliados_ativos: st.caption("Nenhuma base aliada ativa hoje.")
            for b in aliados_ativos:
                nome = b.get('Name')
                sup = b.get('SupplyLevel', 0)
                with st.expander(f"📍 {nome} ({sup}/200)"):
                    st.progress(min(1.0, sup / 200.0))
                    st.write(f"**Superfície:** {'🛣️ Concreto' if b.get('RunwayIsConcrete') else '🌱 Grama'}")
                    render_hangar_logic(b)

        with col_ax_b:
            st.markdown("### 🔴 Axis Active Bases")
            if not eixo_ativos: st.error("⚠️ Nenhuma base operacional do Eixo detectada.")
            for b in eixo_ativos:
                nome = b.get('Name')
                sup = b.get('SupplyLevel', 0)
                alerta = "🚨 " if sup < 20 else ""
                with st.expander(f"{alerta}📍 {nome} ({sup}/200)"):
                    st.progress(min(1.0, sup / 200.0))
                    st.write(f"**Superfície:** {'🛣️ Concreto' if b.get('RunwayIsConcrete') else '🌱 Grama'}")
                    render_hangar_logic(b)

        st.divider()

        # --- 5. OBJETIVOS ESTRATÉGICOS (SEPARADOS) ---
        st.subheader("🎯 Objetivos e Alvos Prioritários")
        objetivos = [o for o in dados.get('Objectives', []) if o.get('ActiveToday')]
        
        col_all_obj, col_ax_obj = st.columns(2)

        with col_all_obj:
            st.markdown("### 🔵 Allies Targets")
            allies_o = [o for o in objetivos if str(o.get('Coalition', '')).lower() in ['allies', 'allied']]
            for o in allies_o:
                st.markdown(f":blue[🎯 **{o.get('Name')}**]")
                st.caption(traduzir_texto(o.get('Description', '')))

        with col_ax_obj:
            st.markdown("### 🔴 Axis Targets")
            axis_o = [o for o in objetivos if str(o.get('Coalition', '')).lower() == 'axis']
            for o in axis_o:
                st.markdown(f":red[🎯 **{o.get('Name')}**]")
                st.caption(traduzir_texto(o.get('Description', '')))
