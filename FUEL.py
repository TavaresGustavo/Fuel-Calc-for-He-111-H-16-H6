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
        st.caption(f"🛡️ Armamento Fixo: {av['armamento_fixed'] if 'armamento_fixed' in av else av['armamento_fixo']}")
        
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
# ABA 4: FMC (FLIGHT MANAGEMENT COMPUTER) - COMPLETO
# ==========================================
with tab4:
    st.header("🚀 Monitor de Execução de Missão (FMC)")
    
    if not st.session_state.get('navlog_manual'):
        st.info("⚠️ O FMC está em standby. Importe uma rota na Aba 1 ou crie pernas na Aba 3 para começar.")
    else:
        # 1. PARÂMETROS DE PERFORMANCE VERTICAL (VNAV)
        with st.expander("📈 Perfil de Voo & Altitude (VNAV)", expanded=True):
            v1, v2, v3, v4 = st.columns(4)
            with v1: alt_cruzeiro = st.number_input("Altitude Cruzeiro (m)", value=4000, step=500)
            with v2: climb_rate = st.number_input("Razão de Subida (m/s)", value=2.5, step=0.5)
            with v3: descent_rate = st.number_input("Razão de Descida (m/s)", value=4.0, step=0.5)
            with v4: alt_pista = st.number_input("Alt. Aeródromo (m)", value=100, step=50)

            # --- MOTOR DE CÁLCULO DE ROTA (E6B INTEGRADO) ---
            # Pegamos o vento e performance para calcular a trigonometria de cada perna
            nav_tas_fmc = float(st.session_state.get('vel_calc', 320))
            w_dir_fmc = float(st.session_state.vento_dir_cb)
            w_spd_fmc = float(st.session_state.vento_vel_cb * 3.6) # Converter m/s para km/h
            
            pernas_fmc = []
            dist_acumulada = 0
            
            for idx, linha in enumerate(st.session_state.navlog_manual):
                try:
                    dist = float(linha.get("Distância (km)", 0.0))
                    tc = float(linha.get("Rumo (TC)", 0.0))
                    
                    # Cálculo do Triângulo de Ventos (WCA e GS)
                    wa_rad = math.radians(w_dir_fmc - tc)
                    sin_wca = max(-1.0, min(1.0, (w_spd_fmc * math.sin(wa_rad)) / nav_tas_fmc))
                    wca_deg = math.degrees(math.asin(sin_wca))
                    th_deg = (tc + wca_deg + 360) % 360
                    gs_leg = max(1.0, (nav_tas_fmc * math.cos(math.radians(wca_deg))) - (w_spd_fmc * math.cos(wa_rad)))
                    tempo_seg = (dist / gs_leg) * 3600
                    
                    dist_acumulada += dist
                    pernas_fmc.append({
                        "id": idx,
                        "nome": linha.get("Perna", f"WP {idx}"),
                        "proa": th_deg,
                        "tempo": tempo_seg,
                        "dist_total": dist_acumulada
                    })
                except: continue

            # --- GRÁFICO DE PERFIL VERTICAL ---
            if pernas_fmc:
                total_missao_km = pernas_fmc[-1]['dist_total']
                # Cálculo de TOC (Top of Climb) e TOD (Top of Descent)
                # Distância = (Tempo de subida) * Velocidade
                dist_subida = ((alt_cruzeiro - alt_pista) / climb_rate) * (nav_tas_fmc / 3600)
                dist_descida = ((alt_cruzeiro - alt_pista) / descent_rate) * (nav_tas_fmc / 3600)
                
                df_vnav = pd.DataFrame({
                    "Distância (km)": [0, dist_subida, max(dist_subida, total_missao_km - dist_descida), total_missao_km],
                    "Altitude (m)": [alt_pista, alt_cruzeiro, alt_cruzeiro, alt_pista]
                })
                st.area_chart(df_vnav.set_index("Distância (km)"))
                st.caption(f"🏔️ TOC: {dist_subida:.1f} km | 📉 TOD: {total_missao_km - dist_descida:.1f} km")

        st.divider()

        # 2. HUD DE EXECUÇÃO (CRONÓMETRO ATIVO)
        @st.fragment(run_every="1s")
        def monitor_fmc_ativo():
            idx_ativo = st.session_state.index_perna_ativa
            
            if idx_ativo >= len(pernas_fmc):
                st.balloons()
                st.success("🏁 MISSÃO CUMPRIDA! TODOS OS WAYPOINTS ATINGIDOS.")
                if st.button("🔄 Reiniciar FMC"):
                    st.session_state.index_perna_ativa = 0
                    st.session_state.cronometro_rodando = False
                    st.rerun()
                return

            p = pernas_fmc[idx_ativo]
            h1, h2, h3 = st.columns([2, 1, 1])
            
            with h1:
                st.subheader(f"📍 Ativo: {p['nome']}")
                st.markdown(f"## 🧭 PROA: **{p['proa']:.0f}°**")
                st.caption(f"Perna {idx_ativo + 1} de {len(pernas_fmc)}")
            
            with h2:
                if st.session_state.cronometro_rodando:
                    decorrido = time.time() - st.session_state.tempo_inicio_perna
                    restante = max(0, p['tempo'] - decorrido)
                    m, s = divmod(int(restante), 60)
                    st.metric("Tempo para WP", f"{m:02d}:{s:02d}")
                    if restante <= 0: 
                        st.toast(f"🔔 WP ATINGIDO! Curvar para {p['proa']:.0f}°", icon="⚠️")
                else:
                    m, s = divmod(int(p['tempo']), 60)
                    st.metric("Estimativa (ETE)", f"{m:02d}:{s:02d}")

            with h3:
                # Controles de Voo
                if not st.session_state.cronometro_rodando:
                    if st.button("▶️ START PERNA", use_container_width=True):
                        st.session_state.cronometro_rodando = True
                        st.session_state.tempo_inicio_perna = time.time()
                        st.rerun()
                else:
                    if st.button("⏭️ PRÓXIMA", use_container_width=True):
                        st.session_state.index_perna_ativa += 1
                        st.session_state.tempo_inicio_perna = time.time()
                        st.rerun()
                    if st.button("⏹️ ABORTAR", use_container_width=True):
                        st.session_state.cronometro_rodando = False
                        st.rerun()

            # Mini Progress Bar da Missão
            progresso = (idx_ativo / len(pernas_fmc))
            st.progress(progresso, text=f"Progresso da Rota: {int(progresso*100)}%")

        monitor_fmc_ativo()
# ==========================================
# ABA 5: INTELIGÊNCIA GLOBAL (C4ISR)
# ==========================================
with tab5:
    st.header("🌐 Inteligência Tática e Logística")
    
    if st.session_state.dados_campanha:
        dados = st.session_state.dados_campanha
        
        # --- 1. BRIEFING DO COMANDO (TRADUZIDO) ---
        st.subheader("📜 Relatório de Operações")
        texto_hoje = dados.get('CurrentDayStateDescription', '')
        texto_ontem = dados.get('PreviousDaysEventsDescription', '')
        
        if texto_hoje:
            with st.container():
                st.info(f"**Briefing Atual:**\n\n{traduzir_texto(texto_hoje)}")
        
        if texto_ontem:
            with st.expander("Ver Resumo das Operações Anteriores"):
                st.write(traduzir_texto(texto_ontem))
        
        st.divider()
        
        # --- 2. OBJETIVOS E INFRAESTRUTURA ---
        col_obj, col_base = st.columns([1, 1])
        
        with col_obj:
            st.subheader("🎯 Objetivos Estratégicos")
            st.caption("Alvos ativos para a missão atual")
            
            objetivos = dados.get('Objectives', [])
            objetivos_ativos = [o for o in objetivos if o.get('ActiveToday') == True]
            
            if objetivos_ativos:
                for obj in objetivos_ativos[:10]: # Mostra os 10 principais
                    # Filtro de Coalizão Robusto
                    coal = str(obj.get('Coalition', '')).strip().lower()
                    if coal in ['allied', 'allies']:
                        icone = "🔵 Aliado"
                    elif coal == 'axis':
                        icone = "🔴 Eixo"
                    else:
                        icone = "⚪ Neutro"
                    
                    tipo = traduzir_texto(obj.get('Type', 'Instalação'))
                    st.error(f"**{obj.get('Name', 'Alvo')}** ({tipo}) - {icone}")
            else:
                st.write("Nenhum objetivo terrestre prioritário listado.")

        with col_base:
            st.subheader("🛫 Gestão de Aeródromos")
            airfields = dados.get('Airfields', [])
            
            if airfields:
                lista_nomes_bases = [b.get('Name', 'Base') for b in airfields]
                base_selecionada = st.selectbox("Inspecionar Base:", lista_nomes_bases)
                
                # Localiza os dados da base escolhida
                b_dados = next((b for b in airfields if b.get('Name') == base_selecionada), None)
                
                if b_dados:
                    # --- Status de Alerta ---
                    sob_ataque = b_dados.get('UnderAttack', False) or b_dados.get('IsUnderAttack', False)
                    if sob_ataque:
                        st.error("🚨 **ALERTA: BASE SOB ATAQUE INIMIGO!** 🚨")
                    else:
                        st.success("✅ **Status: Base Segura**")
                    
                    st.divider()
                    
                    # --- Dados da Pista ---
                    brg = b_dados.get('RunwayBearing', 0)
                    is_conc = b_dados.get('RunwayIsConcrete', False)
                    tipo_piso = "🛣️ Concreto / Asfalto" if is_conc else "🌱 Grama / Terra"
                    
                    st.caption("Configuração da Pista")
                    st.write(f"**Proa (QDM):** {brg:03.0f}° / {(brg + 180) % 360:03.0f}°")
                    st.write(f"**Superfície:** {tipo_piso}")
                    
                    # --- Nível de Suprimentos (Barra Visual) ---
                    sup_val = max(0, min(100, int(b_dados.get('SupplyLevel', 0))))
                    st.progress(sup_val / 100.0, text=f"📦 Logística / Suprimentos: {sup_val}%")
                    
                    st.divider()
                    
                    # --- Inventário do Hangar ---
                    st.caption("Aeronaves em Stock")
                    avioes_hangar = b_dados.get('AvailableAirframes', [])
                    if avioes_hangar:
                        for av in avioes_hangar:
                            nome_av = av.get('Type', 'Aeronave')
                            qtd = av.get('NumberAvailable', 0)
                            st.write(f"- {nome_av}: **{qtd}** unid.")
                    else:
                        st.write("Sem aeronaves disponíveis nesta base.")
            else:
                st.info("Nenhum dado de aeródromo recebido do servidor.")

    else:
        st.warning("📡 Aguardando sincronização com o servidor do Combat Box para carregar dados de inteligência...")
