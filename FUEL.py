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
if 'vento_vel_cb'    not in st.session_state: st.session_state.vento_vel_cb    = 5.0
if 'vento_dir_cb'    not in st.session_state: st.session_state.vento_dir_cb    = 45.0
if 'temp_cb'         not in st.session_state: st.session_state.temp_cb         = 15.0
if 'status_cb'       not in st.session_state: st.session_state.status_cb       = "A aguardar sincronização..."
if 'dados_campanha'  not in st.session_state: st.session_state.dados_campanha  = None
if 'temp_amanha_cb'       not in st.session_state: st.session_state.temp_amanha_cb       = 15.0
if 'vento_vel_amanha_cb'  not in st.session_state: st.session_state.vento_vel_amanha_cb  = 5.0
if 'vento_dir_amanha_cb'  not in st.session_state: st.session_state.vento_dir_amanha_cb  = 45.0
if 'navlog_manual'   not in st.session_state:
    st.session_state.navlog_manual = [{"Perna": "Base -> Alvo", "Distancia (km)": 50.0, "Rumo (TC)": 90.0, "TAS (km/h)": 330, "Altitude (m)": 2000}]
if 'index_perna_ativa'              not in st.session_state: st.session_state.index_perna_ativa              = 0
if 'cronometro_rodando'             not in st.session_state: st.session_state.cronometro_rodando             = False
if 'tempo_inicio_perna'             not in st.session_state: st.session_state.tempo_inicio_perna             = None
if 'tempo_pausado_acumulado'        not in st.session_state: st.session_state.tempo_pausado_acumulado        = 0.0
if 'tempo_inicio_missao_absoluto'   not in st.session_state: st.session_state.tempo_inicio_missao_absoluto   = None
if 'vel_calc'        not in st.session_state: st.session_state.vel_calc        = 320.0
if 'dist_calc'       not in st.session_state: st.session_state.dist_calc       = 250.0
if 'last_file_hash'  not in st.session_state: st.session_state.last_file_hash  = None
if 'av_nome_selecionado' not in st.session_state: st.session_state.av_nome_selecionado = "He-111 H-16"

# ==========================================
# 1. FUNCOES DA API E TRADUCAO
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
            st.session_state.status_cb = f"Erro HTTP {response.status_code}"
            return
        dados_json = response.json()
        st.session_state.dados_campanha = dados_json
        weather_hoje = dados_json.get("Weather", {})
        wind_hoje    = weather_hoje.get("WindAtGroundLevel", {})
        st.session_state.temp_cb      = float(weather_hoje.get("Temperature", 15.0))
        st.session_state.vento_vel_cb = float(wind_hoje.get("Speed", 5.0))
        bearing_bruto = float(wind_hoje.get("Bearing", 45.0))
        st.session_state.vento_dir_cb = (bearing_bruto + 180) % 360
        weather_amanha = dados_json.get("WeatherTomorrow", {})
        wind_amanha    = weather_amanha.get("WindAtGroundLevel", {})
        st.session_state.temp_amanha_cb      = float(weather_amanha.get("Temperature", 15.0))
        st.session_state.vento_vel_amanha_cb = float(wind_amanha.get("Speed", 5.0))
        bearing_amanha_bruto = float(wind_amanha.get("Bearing", 45.0))
        st.session_state.vento_dir_amanha_cb = (bearing_amanha_bruto + 180) % 360
        st.session_state.status_cb = "API Sincronizada!"
    except Exception as e:
        st.session_state.status_cb = f"Erro de Ligacao: {e}"

def calcular_rumo_e_distancia(p1, p2):
    # lat cresce para NORTE, lng cresce para LESTE
    # Fator 3.872 km/grau calibrado para mapa Rheinland (IL-2 Mission Planner)
    dlng = p2['lng'] - p1['lng']
    dlat = p2['lat'] - p1['lat']
    rumo_final   = (math.degrees(math.atan2(dlng, dlat)) + 360) % 360
    distancia_km = math.sqrt(dlng**2 + dlat**2) * 3.872
    return rumo_final, distancia_km

# ==========================================
# 2.1 BASE DE DADOS: ALTITUDES
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
# 2. BASE DE DADOS: AERONAVES
# ==========================================
db_avioes = {
    "He-111 H-16": {
        "peso_base_sem_combustivel": 9300, "peso_max": 14000, "consumo_l_min": 10.2,
        "vel_cruzeiro_padrao": 330, "tanque_max_l": 3450,
        "climb_rate_default": 2.5, "descent_rate_default": 4.0,
        "armamento_fixo": "4x 7.92mm MG-81J | 1x 20mm MG-FF | 1x 13mm MG-131",
        "modificacoes": {"Padrao": 0, "Remover Blindagem": -115, "Tanque Adicional": 150},
        "presets_bombas": {"Vazio": 0, "1x SC 2500 (Max)": 2400, "2x SC 1800 (Satan)": 3560,
                           "2x SC 1000 (Hermann)": 2180, "8x SC 250": 2000, "32x SC 50": 1600}
    },
    "He-111 H-6": {
        "peso_base_sem_combustivel": 9500, "peso_max": 14000, "consumo_l_min": 10.5,
        "vel_cruzeiro_padrao": 320, "tanque_max_l": 3450,
        "climb_rate_default": 2.5, "descent_rate_default": 4.0,
        "armamento_fixo": "6x 7.92mm MG-15",
        "modificacoes": {"Padrao": 0, "Torre Frontal (20mm)": 46, "Torre Ventral": 147, "Kit Anti-Navio": 193},
        "presets_bombas": {"Vazio": 0, "2x SC 1000": 2180, "1x SC 1800": 1780, "4x SC 250": 1000, "16x SC 50": 800}
    },
    "Ju-52/3M": {
        "peso_base_sem_combustivel": 7500, "peso_max": 11000, "consumo_l_min": 12.0,
        "vel_cruzeiro_padrao": 240, "tanque_max_l": 2450,
        "climb_rate_default": 2.0, "descent_rate_default": 3.0,
        "armamento_fixo": "1x 13mm MG-131 (Dorsal)",
        "modificacoes": {"Padrao": 0, "Paraquedistas (12 homens)": 1200, "Carga Interna Tatica": 2300, "Rodas de Inverno": 45},
        "presets_bombas": {"Vazio": 0, "10x MAB 250 (Containers)": 2550, "12x SC 50": 600}
    },
    "Ju-88 A-4": {
        "peso_base_sem_combustivel": 8600, "peso_max": 14000, "consumo_l_min": 10.0,
        "vel_cruzeiro_padrao": 370, "tanque_max_l": 1680,
        "climb_rate_default": 3.5, "descent_rate_default": 5.0,
        "armamento_fixo": "1x 13mm MG-131 | 3x 7.92mm MG-81J",
        "modificacoes": {"Padrao": 0, "Sem Dive Brakes": -60, "Sem Gondola Inferior": -123, "Camera de Reconhecimento": 25},
        "presets_bombas": {"Vazio": 0, "4x SC 500": 2000, "10x SC 50 (Interno)": 500,
                           "28x SC 50 (Full Load)": 1400, "2x SC 1000": 2180}
    }
}

# ==========================================
# 3. INTERFACE E BARRA LATERAL
# ==========================================
st.set_page_config(page_title="Painel Tatico - Combat Box", layout="wide")
st.markdown("""<style>.stApp { background-color: #0E1117; color: #FAFAFA; }</style>""", unsafe_allow_html=True)

with st.sidebar:
    st.header("Comando e Controlo")
    st.markdown("Telemetria em tempo real (Atualiza a cada 60s).")

    @st.fragment(run_every="60s")
    def painel_telemetria_ativo():
        fetch_combatbox_data()
        st.info(st.session_state.status_cb)
        st.divider()
        dados = st.session_state.dados_campanha
        if dados:
            dia_obj   = dados.get("Day", {})
            dia_num   = dia_obj.get("DayInCampaign", "?")
            dia_str   = f"{dia_obj.get('Day','?')}/{dia_obj.get('Month','?')}/{dia_obj.get('Year','?')}"
            vencendo  = dados.get("WinningCoalition", "--")
            restantes = dados.get("DaysRemaining", "?")
            st.markdown(f"**Dia {dia_num}** - {dia_str}")
            st.markdown(f"**Vencendo:** {vencendo} | **Restam:** {restantes} dias")
            st.divider()
        st.markdown("**METEOROLOGIA: HOJE**")
        st.metric("Vento",      f"{st.session_state.vento_vel_cb} m/s")
        st.metric("Direcao",    f"{st.session_state.vento_dir_cb:.0f}")
        st.metric("Temperatura",f"{st.session_state.temp_cb} C")
        st.divider()
        st.markdown("**METEOROLOGIA: AMANHA**")
        st.metric("Vento",      f"{st.session_state.vento_vel_amanha_cb} m/s")
        st.metric("Direcao",    f"{st.session_state.vento_dir_amanha_cb:.0f}")
        st.metric("Temperatura",f"{st.session_state.temp_amanha_cb} C")
        st.caption(f"Ultima sincronizacao: {time.strftime('%H:%M:%S')}")

    painel_telemetria_ativo()

st.title("Painel Tatico C4ISR - IL-2 Combat Box")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["Hangar", "Lotfe 7", "NavLog & E6B", "FMC (Ativo)", "Inteligencia"])

# ==========================================
# ABA 1: HANGAR
# ==========================================
with tab1:
    st.header("Configuracao de Carga e Rota")
    col_f, col_clear = st.columns([3, 1])
    with col_f:
        arquivo_plano = st.file_uploader("Importar Plano de Voo (.json)", type=["json"])
        if arquivo_plano is not None:
            file_content = arquivo_plano.getvalue()
            current_hash = hash(file_content)
            if st.session_state.get('last_file_hash') != current_hash:
                st.session_state.last_file_hash = current_hash
                try:
                    dados_plano = json.loads(file_content)
                    if "routes" in dados_plano:
                        plano = next((r for r in dados_plano["routes"] if r.get("isFlightPlan")), None)
                        if plano is None:
                            st.error("Nenhuma rota de plano de voo encontrada. Marque uma rota como Flight Plan no Mission Planner.")
                        else:
                            coords    = plano["latLngs"]
                            speeds    = plano.get("speeds", [])
                            altitudes = plano.get("altitudes", [])
                            navlog_temp = []
                            dist_total  = 0.0
                            for i in range(len(coords) - 1):
                                rumo, dist = calcular_rumo_e_distancia(coords[i], coords[i+1])
                                dist_total += dist
                                vel_p = int(speeds[i])      if i < len(speeds)         else int(plano.get("speed", 330))
                                alt_p = int(altitudes[i+1]) if i+1 < len(altitudes)   else int(plano.get("altitude", 2000))
                                navlog_temp.append({
                                    "Perna":          f"WP {i} -> WP {i+1}",
                                    "Distancia (km)": round(dist, 1),
                                    "Rumo (TC)":      round(rumo, 0),
                                    "TAS (km/h)":     vel_p,
                                    "Altitude (m)":   alt_p
                                })
                            st.session_state.navlog_manual = navlog_temp
                            st.session_state.dist_calc     = dist_total
                            if navlog_temp:
                                st.session_state.vel_calc = float(navlog_temp[0]["TAS (km/h)"])
                            st.success(f"{len(navlog_temp)} pernas extraidas de '{plano.get('name','Rota')}' -> NavLog atualizado!")
                    else:
                        st.session_state.navlog_manual = dados_plano
                        st.session_state.dist_calc = sum(item.get("Distancia (km)", 0) for item in dados_plano)
                        st.success("Rota carregada!")
                except Exception as e:
                    st.error(f"Erro ao processar JSON: {e}")

    with col_clear:
        if st.button("Reset Rota", use_container_width=True):
            st.session_state.navlog_manual = []
            st.session_state.dist_calc = 100.0
            st.rerun()

    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        av_nome = st.selectbox("Selecione a Aeronave", list(db_avioes.keys()))
        st.session_state.av_nome_selecionado = av_nome
        av = db_avioes[av_nome]
        missao_dist = st.number_input("Distancia da Missao (km)", value=float(st.session_state.get('dist_calc', 100.0)))
        missao_vel  = st.number_input("Velocidade de Cruzeiro (km/h)", value=float(av['vel_cruzeiro_padrao']))
        margem_seg  = st.slider("Reserva de Combustivel (%)", 0, 100, 30)
    with c2:
        mod_sel  = st.selectbox("Modificacoes",    list(av['modificacoes'].keys()))
        bomb_sel = st.selectbox("Carga de Bombas", list(av['presets_bombas'].keys()))
        st.caption(f"Armamento Fixo: {av.get('armamento_fixo','Nao listado')}")

    if missao_vel > 0:
        tempo_estimado = (missao_dist / missao_vel) * 60
        comb_l    = tempo_estimado * av['consumo_l_min'] * (1 + (margem_seg / 100))
        peso_total = (av['peso_base_sem_combustivel']
                      + av['modificacoes'][mod_sel]
                      + av['presets_bombas'][bomb_sel]
                      + (comb_l * 0.72))
        st.divider()
        col_res1, col_res2, col_res3 = st.columns(3)
        with col_res1:
            if peso_total <= av['peso_max']:
                st.success(f"Peso Total: {peso_total:.0f} kg / {av['peso_max']} kg")
            else:
                st.error(f"SOBRECARGA: {peso_total:.0f} kg / {av['peso_max']} kg")
        with col_res2:
            excede = " - EXCEDE TANQUE!" if comb_l > av['tanque_max_l'] else ""
            if comb_l > av['tanque_max_l']:
                st.error(f"Combustivel: {comb_l:.0f} L{excede}")
            else:
                st.info(f"Combustivel: {comb_l:.0f} L (max {av['tanque_max_l']} L)")
        with col_res3:
            st.info(f"Tempo estimado: {tempo_estimado:.0f} min ({tempo_estimado/60:.1f}h)")

# ==========================================
# ABA 2: LOTFE 7
# ==========================================
with tab2:
    st.markdown("""
        <style>
            .stSlider [data-baseweb="slider"] { height: 45px; }
            .stSlider [data-baseweb="thumb"]  { height: 40px; width: 40px; background-color: #FF4B4B; }
        </style>
    """, unsafe_allow_html=True)

    st.header("Ajuste de Vento da Mira (Lofte 7)")
    st.caption("Calcule os parametros de entrada do Lofte 7 a partir da proa e vento.")

    usar_api_vento = False
    if st.session_state.dados_campanha:
        col_btn, col_info = st.columns([1, 3])
        with col_btn:
            usar_api_vento = st.button("Preencher com Vento da API")
        with col_info:
            st.caption(f"API atual: {st.session_state.vento_vel_cb} m/s de {st.session_state.vento_dir_cb:.0f}")

    phead  = st.slider("PLANE HEADING", 0, 359, value=0, step=1, key="phdg_lofte")
    whead_default  = int(st.session_state.vento_dir_cb) if usar_api_vento else 0
    wspeed_default = int(st.session_state.vento_vel_cb) if usar_api_vento else 0
    whead  = st.slider("WIND DIRECTION (FROM)", 0, 359, value=whead_default,  step=1, key="whdg_lofte")
    wspeed = st.slider("WIND SPEED (m/s)",       0,  30, value=wspeed_default, step=1, key="wspeed_lofte")

    raw_hdg          = (whead - phead) % 360
    sight_wind_hdg   = raw_hdg if raw_hdg <= 180 else raw_hdg - 360
    sight_wind_speed = wspeed

    st.divider()
    res1, res2 = st.columns(2)
    with res1:
        st.metric(label="Sight Wind Hdg",   value=f"{sight_wind_hdg:+d}")
        st.caption("Gire o seletor de direcao na mira para este valor.")
    with res2:
        st.metric(label="Sight Wind Speed", value=f"{sight_wind_speed} m/s")
        st.caption("Ajuste a forca do vento na engrenagem da mira.")

    if sight_wind_speed > 0:
        direcao_txt = "DIREITA" if sight_wind_hdg > 0 else ("ESQUERDA" if sight_wind_hdg < 0 else "FRONTAL")
        st.info(f"Configure sua mira com {sight_wind_hdg:+d} ({direcao_txt}) e {sight_wind_speed} m/s antes do bomb run.")

# ==========================================
# ABA 3: E6B & NAVLOG
# ==========================================
with tab3:
    st.header("Centro de Navegacao")
    st.caption("Importe o plano de voo na Aba 1 (Hangar) para preencher o NavLog automaticamente.")
    st.divider()

    c_tas, c_dir, c_vel = st.columns(3)
    with c_tas:
        def_tas = float(st.session_state.navlog_manual[0].get("TAS (km/h)", st.session_state.vel_calc)) if st.session_state.navlog_manual else float(st.session_state.vel_calc)
        nav_tas = st.number_input("Sua TAS esperada (km/h)", value=def_tas, step=10.0)
    with c_dir:
        nav_w_dir = st.number_input("Vento vindo DE", value=float(st.session_state.vento_dir_cb), key="nav_dir_e6b")
    with c_vel:
        nav_w_spd = st.number_input("Vel. Vento (km/h)", value=float(st.session_state.vento_vel_cb * 3.6), step=5.0, key="nav_spd_e6b")

    st.subheader("Navigation Log (Diario de Rota)")
    navlog_editado = st.data_editor(
        st.session_state.navlog_manual,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Perna":          st.column_config.TextColumn("Nome da Perna"),
            "Distancia (km)": st.column_config.NumberColumn("Distancia (km)", format="%.1f"),
            "Rumo (TC)":      st.column_config.NumberColumn("Rumo Mapa (TC)", format="%.0f"),
            "TAS (km/h)":     st.column_config.NumberColumn("TAS (km/h)"),
            "Altitude (m)":   st.column_config.NumberColumn("Altitude (m)")
        }
    )
    st.session_state.navlog_manual = navlog_editado

    if len(navlog_editado) > 0:
        resultados_finais = []
        for linha in navlog_editado:
            try:
                dist   = float(linha.get("Distancia (km)", 0.0))
                tc_deg = float(linha.get("Rumo (TC)", 0.0))
            except:
                dist, tc_deg = 0.0, 0.0
            nome_perna = linha.get("Perna", "N/D")
            if dist > 0:
                wa_rad = math.radians(nav_w_dir - tc_deg)
                try:
                    sin_wca = max(-1.0, min(1.0, (nav_w_spd * math.sin(wa_rad)) / nav_tas))
                    wca_deg = math.degrees(math.asin(sin_wca))
                except:
                    wca_deg = 0.0
                th_deg  = (tc_deg + wca_deg + 360) % 360
                gs_leg  = (nav_tas * math.cos(math.radians(wca_deg))) - (nav_w_spd * math.cos(wa_rad))
                gs_leg  = max(1.0, gs_leg)
                tempo_min = (dist / gs_leg) * 60
                resultados_finais.append({
                    "Perna":        nome_perna,
                    "Rumo Mapa":    f"{tc_deg:.0f}",
                    "Voar PROA (TH)": f"{th_deg:.0f}",
                    "Vel. Solo (GS)": f"{gs_leg:.0f} km/h",
                    "Tempo Voo":    f"{tempo_min:.1f} min"
                })
        if resultados_finais:
            st.table(resultados_finais)

    st.divider()
    st.subheader("Computador E6B")
    col_tsd, col_conv = st.columns(2)
    with col_tsd:
        st.markdown("**Tempo, Velocidade, Distancia (TSD)**")
        modo_tsd = st.radio("Calcular:", ["Tempo", "Distancia", "Velocidade (GS)"], horizontal=True)
        if modo_tsd == "Tempo":
            d_in = st.number_input("Distancia (km)", value=50.0, key="d_t")
            v_in = st.number_input("Velocidade (km/h)", value=300.0, key="v_t")
            if v_in > 0: st.info(f"Resultado: {(d_in/v_in)*60:.1f} minutos")
        elif modo_tsd == "Distancia":
            t_in = st.number_input("Tempo (min)", value=10.0, key="t_d")
            v_in = st.number_input("Velocidade (km/h)", value=300.0, key="v_d")
            st.info(f"Resultado: {v_in*(t_in/60):.1f} km")
        else:
            d_in = st.number_input("Distancia (km)", value=50.0, key="d_v")
            t_in = st.number_input("Tempo (min)", value=10.0, key="t_v")
            if t_in > 0: st.info(f"Resultado: {d_in/(t_in/60):.0f} km/h")
    with col_conv:
        st.markdown("**Conversoes**")
        cat_conv = st.selectbox("Unidade:", ["Velocidade (km/h e mph)", "Altitude (metros e pes)"])
        val_conv = st.number_input("Valor:", value=1000.0 if "Altitude" in cat_conv else 300.0)
        if "Velocidade" in cat_conv:
            st.warning(f"{val_conv} km/h = {val_conv/1.60934:.0f} mph")
            st.warning(f"{val_conv} mph = {val_conv*1.60934:.0f} km/h")
        else:
            st.warning(f"{val_conv} metros = {val_conv*3.28084:.0f} pes")
            st.warning(f"{val_conv} pes = {val_conv/3.28084:.0f} metros")

# ==========================================
# ABA 4: FMC
# ==========================================
with tab4:
    st.header("Flight Management Computer")

    if not st.session_state.get('navlog_manual'):
        st.info("Configure uma rota na Aba 1 (Hangar) para ativar o FMC.")
    else:
        lista_aerodromos_db = sorted(list(db_altitudes_tecnico.keys()))

        with st.expander("Configuracao de Aerodromos", expanded=True):
            col_dep, col_arr = st.columns(2)
            with col_dep:
                base_dep = st.selectbox("Decolagem de:", lista_aerodromos_db, key="fmc_dep_estatico")
                alt_dep  = db_altitudes_tecnico[base_dep]
                st.write(f"Altitude Base: {alt_dep}m")
            with col_arr:
                base_arr = st.selectbox("Destino Final:", lista_aerodromos_db, key="fmc_arr_estatico")
                alt_arr  = db_altitudes_tecnico[base_arr]
                st.write(f"Altitude Alvo: {alt_arr}m")

        av_nome_fmc = st.session_state.get('av_nome_selecionado', "He-111 H-16")
        av_fmc      = db_avioes.get(av_nome_fmc, {})
        st.caption(f"Aeronave: {av_nome_fmc}")

        with st.expander("Perfil de Voo (VNAV)", expanded=True):
            v1, v2, v3, v4 = st.columns(4)
            with v1: alt_cruzeiro = st.number_input("Cruzeiro (m)", value=4000, step=500)
            with v2: climb_rate   = st.number_input("Subida (m/s)",  value=float(av_fmc.get('climb_rate_default', 2.5)))
            with v3: descent_rate = st.number_input("Descida (m/s)", value=float(av_fmc.get('descent_rate_default', 4.0)))
            with v4: st.number_input("Alt. Aerodromos (m)", value=alt_arr, disabled=True)

        nav_tas = float(st.session_state.get('vel_calc', 320))
        w_dir   = float(st.session_state.get('vento_dir_cb', 45.0))
        w_spd   = float(st.session_state.get('vento_vel_cb', 5.0) * 3.6)

        pernas_fmc = []
        dist_acum  = 0.0
        for idx, linha in enumerate(st.session_state.navlog_manual):
            try:
                dist = float(linha.get("Distancia (km)", linha.get("Distância (km)", 0.0)))
                tc   = float(linha.get("Rumo (TC)", 0.0))
                wa_rad  = math.radians(w_dir - tc)
                sin_wca = max(-1.0, min(1.0, (w_spd * math.sin(wa_rad)) / nav_tas))
                wca     = math.degrees(math.asin(sin_wca))
                th      = (tc + wca + 360) % 360
                gs      = max(1.0, (nav_tas * math.cos(math.radians(wca))) - (w_spd * math.cos(wa_rad)))
                tempo   = (dist / gs) * 3600
                dist_acum += dist
                pernas_fmc.append({"id": idx, "nome": linha.get("Perna", f"WP{idx}"),
                                   "proa": th, "tempo": tempo, "dist_total": dist_acum})
            except:
                continue

        if pernas_fmc:
            total_km     = pernas_fmc[-1]['dist_total']
            dist_climb   = max(0.0, ((alt_cruzeiro - alt_dep)  / max(climb_rate,   0.1)) * (nav_tas / 3600))
            dist_descent = max(0.0, ((alt_cruzeiro - alt_arr)  / max(descent_rate, 0.1)) * (nav_tas / 3600))
            if dist_climb + dist_descent > total_km:
                factor       = total_km / (dist_climb + dist_descent)
                dist_climb   *= factor
                dist_descent *= factor
            tod_km = total_km - dist_descent

            df_vnav = pd.DataFrame({
                "Distancia (km)": [0, dist_climb, tod_km, total_km],
                "Altitude (m)":   [alt_dep, alt_cruzeiro, alt_cruzeiro, alt_arr]
            })
            st.area_chart(df_vnav.set_index("Distancia (km)"))

        st.divider()

        @st.fragment(run_every="1s")
        def fmc_hud_final():
            idx = st.session_state.index_perna_ativa
            if idx < len(pernas_fmc):
                p = pernas_fmc[idx]
                h1, h2, h3 = st.columns([2, 1, 1])
                with h1:
                    st.subheader(f"Perna: {p['nome']}")
                    st.markdown(f"## PROA: {p['proa']:.0f}")
                with h2:
                    if st.session_state.cronometro_rodando and st.session_state.tempo_inicio_perna:
                        passado  = time.time() - st.session_state.tempo_inicio_perna
                        restante = max(0, p['tempo'] - passado)
                        m, s     = divmod(int(restante), 60)
                        st.metric("Tempo WP", f"{m:02d}:{s:02d}")
                    else:
                        st.metric("Tempo WP", "--:--")
                if pernas_fmc and st.session_state.cronometro_rodando and st.session_state.tempo_inicio_missao_absoluto:
                    tempo_total_seg      = time.time() - st.session_state.tempo_inicio_missao_absoluto
                    distancia_percorrida = (tempo_total_seg / 3600) * nav_tas
                    dist_para_tod        = tod_km - distancia_percorrida
                    st.divider()
                    if 0 < dist_para_tod <= 10:
                        st.warning(f"PREPARAR DESCIDA: TOD em {dist_para_tod:.1f} km")
                    elif dist_para_tod <= 0:
                        st.error(f"INICIAR DESCIDA! Passou {abs(dist_para_tod):.1f} km do TOD")
                    else:
                        st.info(f"Cruzeiro Estavel. Descida em {dist_para_tod:.1f} km")
                with h3:
                    if not st.session_state.cronometro_rodando:
                        if st.button("START", use_container_width=True):
                            st.session_state.cronometro_rodando           = True
                            st.session_state.tempo_inicio_perna           = time.time()
                            st.session_state.tempo_inicio_missao_absoluto = time.time()
                            st.rerun()
                    else:
                        if st.button("NEXT", use_container_width=True):
                            st.session_state.index_perna_ativa += 1
                            st.session_state.tempo_inicio_perna = time.time()
                            st.rerun()
            else:
                st.success("Objetivo Atingido!")
                if st.button("Reiniciar FMC"):
                    st.session_state.index_perna_ativa            = 0
                    st.session_state.cronometro_rodando           = False
                    st.session_state.tempo_inicio_missao_absoluto = None
                    st.rerun()

        fmc_hud_final()

# ==========================================
# ABA 5: INTELIGENCIA TATICA
# ==========================================
with tab5:
    st.header("Inteligencia Tatica e Logistica (C4ISR)")

    if not st.session_state.get('dados_campanha'):
        st.warning("Aguardando sincronizacao com o servidor do Combat Box...")
    else:
        dados     = st.session_state.dados_campanha
        airfields = dados.get('Airfields', [])

        st.subheader("Briefing de Operacoes")
        texto_hoje = dados.get('CurrentDayStateDescription', '')
        if texto_hoje:
            st.info(f"Briefing do Dia:\n\n{traduzir_texto(texto_hoje)}")
        with st.expander("Ver Resumo das Operacoes Anteriores"):
            texto_ontem = dados.get('PreviousDaysEventsDescription', '')
            st.write(traduzir_texto(texto_ontem) if texto_ontem else "Sem registros.")

        front_mov = dados.get('FrontLineMovementSummary', '')
        if front_mov:
            with st.expander("Movimento da Linha de Frente"):
                st.write(traduzir_texto(front_mov))

        st.divider()

        # Baixas
        st.subheader("Balanco de Perdas")
        col_la, col_lx = st.columns(2)
        losses = dados.get('Losses', {})
        losses_allied = losses.get('Allied', losses.get('LossesAllied', {}))
        losses_axis   = losses.get('Axis',   losses.get('LossesAxis',   {}))
        with col_la:
            st.markdown("**Aliados**")
            if losses_allied:
                st.metric("Aeronaves", losses_allied.get('Aircraft', '--'))
                st.metric("Pilotos",   losses_allied.get('Pilots',   '--'))
                st.metric("Veiculos",  losses_allied.get('Vehicles', '--'))
            else:
                st.caption("Sem dados.")
        with col_lx:
            st.markdown("**Eixo**")
            if losses_axis:
                st.metric("Aeronaves", losses_axis.get('Aircraft', '--'))
                st.metric("Pilotos",   losses_axis.get('Pilots',   '--'))
                st.metric("Veiculos",  losses_axis.get('Vehicles', '--'))
            else:
                st.caption("Sem dados.")

        st.divider()

        # Streaks
        streaks_allied = dados.get('PilotStreaksAllied', [])
        streaks_axis   = dados.get('PilotStreaksAxis',   [])
        if streaks_allied or streaks_axis:
            st.subheader("Pilotos em Destaque (Streaks)")
            col_sa, col_sx = st.columns(2)
            with col_sa:
                st.markdown("**Aliados**")
                for p in streaks_allied[:5]:
                    st.write(f"- {p.get('Pilot','?')}: {p.get('Streak','?')} kills")
            with col_sx:
                st.markdown("**Eixo**")
                for p in streaks_axis[:5]:
                    st.write(f"- {p.get('Pilot','?')}: {p.get('Streak','?')} kills")
            st.divider()

        # Paraquedistas
        para_ops = dados.get('ParatrooperOps', [])
        if para_ops:
            with st.expander(f"Operacoes de Paraquedistas ({len(para_ops)})"):
                df_para = pd.DataFrame(para_ops)
                st.dataframe(df_para, use_container_width=True)
            st.divider()

        def filtrar_bases_por_atividade(lista, coalizao_alvo):
            resultado = []
            for b in lista:
                b_coal = str(b.get('Coalition', '')).strip().lower()
                alvos  = [c.lower() for c in coalizao_alvo]
                if b_coal in alvos and str(b.get('ActiveToday', False)).lower() in ['true', '1']:
                    resultado.append(b)
            return resultado

        def render_hangar_logic(base):
            hangar = base.get('AvailableAirframes', [])
            if hangar:
                st.caption("Aeronaves em Hangar:")
                for av in hangar:
                    tipo  = av.get('Type', 'Aeronave')
                    qtd   = int(av.get('NumberAvailable', 0))
                    txt_q = "ILIMITADO" if qtd == -1 else f"{qtd} unid."
                    col_n = av.get('ColloquialName', '')
                    label = f"{tipo}" + (f" ({col_n})" if col_n else "")
                    st.write(f"- {label}: {txt_q}")
            else:
                st.write("Sem estoque de aeronaves.")

        aliados_ativos = filtrar_bases_por_atividade(airfields, ['Allies', 'Allied'])
        eixo_ativos    = filtrar_bases_por_atividade(airfields, ['Axis'])

        st.subheader(f"Bases Ativas: {len(aliados_ativos)} Aliadas | {len(eixo_ativos)} Eixo")
        col_all_b, col_ax_b = st.columns(2)

        with col_all_b:
            st.markdown("### Allies Active Bases")
            if not aliados_ativos:
                st.caption("Nenhuma base aliada ativa hoje.")
            for b in aliados_ativos:
                nome = b.get('Name', '?')
                sup  = b.get('SupplyLevel', 0)
                with st.expander(f"{nome} ({sup}/200)"):
                    st.progress(min(1.0, sup / 200.0))
                    st.write(f"Superficie: {'Concreto' if b.get('RunwayIsConcrete') else 'Grama'}")
                    st.write(f"Grid: {b.get('Grid','--')}")
                    render_hangar_logic(b)

        with col_ax_b:
            st.markdown("### Axis Active Bases")
            if not eixo_ativos:
                st.error("Nenhuma base operacional do Eixo detectada.")
            for b in eixo_ativos:
                nome   = b.get('Name', '?')
                sup    = b.get('SupplyLevel', 0)
                alerta = "ALERTA " if sup < 20 else ""
                with st.expander(f"{alerta}{nome} ({sup}/200)"):
                    st.progress(min(1.0, sup / 200.0))
                    st.write(f"Superficie: {'Concreto' if b.get('RunwayIsConcrete') else 'Grama'}")
                    st.write(f"Grid: {b.get('Grid','--')}")
                    render_hangar_logic(b)

        st.divider()

        st.subheader("Objetivos e Alvos Prioritarios")
        objetivos = [o for o in dados.get('Objectives', []) if o.get('ActiveToday')]
        col_all_obj, col_ax_obj = st.columns(2)

        with col_all_obj:
            st.markdown("### Allies Targets")
            allies_o = [o for o in objetivos if str(o.get('Coalition','')).lower() in ['allies','allied']]
            for o in allies_o:
                sup_max = o.get('MaxSupplyLevel', 100)
                sup_cur = o.get('SupplyLevel', 0)
                st.markdown(f":blue[{o.get('Name')}]")
                st.progress(min(1.0, sup_cur / max(sup_max, 1)), text=f"Supply: {sup_cur}/{sup_max}")
                desc = o.get('Description') or o.get('notes', '')
                if desc: st.caption(traduzir_texto(desc))

        with col_ax_obj:
            st.markdown("### Axis Targets")
            axis_o = [o for o in objetivos if str(o.get('Coalition','')).lower() == 'axis']
            for o in axis_o:
                sup_max = o.get('MaxSupplyLevel', 100)
                sup_cur = o.get('SupplyLevel', 0)
                st.markdown(f":red[{o.get('Name')}]")
                st.progress(min(1.0, sup_cur / max(sup_max, 1)), text=f"Supply: {sup_cur}/{sup_max}")
                desc = o.get('Description') or o.get('notes', '')
                if desc: st.caption(traduzir_texto(desc))
