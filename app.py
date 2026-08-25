import streamlit as st
import os
import json
import io
import time
from datetime import datetime, date
from pathlib import Path
from google import genai
from gtts import gTTS

# ReportLab para exportación PDF profesional
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.units import cm

# --- CONFIGURACIÓN DE PÁGINA (OPTIMIZADA IPAD / DESKTOP) ---
st.set_page_config(
    page_title="Campus Educativo Familiar & VIU",
    page_icon="🐕‍🦺",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- ESTILOS MODERNOS NOTEBOOK / STUDYFETCH ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    .main { background-color: #F8FAFC; }
    
    @keyframes petFloat {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-5px); }
    }
    
    .chopi-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        border: 1px solid #334155;
        border-radius: 20px;
        padding: 16px 22px;
        color: white;
        display: flex;
        align-items: center;
        gap: 16px;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.12);
        margin-bottom: 20px;
    }
    
    .chopi-avatar {
        font-size: 42px;
        background: #1E293B;
        border: 2px solid #F59E0B;
        border-radius: 50%;
        padding: 6px 10px;
        animation: petFloat 3.5s ease-in-out infinite;
    }
    
    .mosaic-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 18px;
        padding: 22px;
        text-align: center;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.04);
        min-height: 190px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .mosaic-card:hover {
        transform: translateY(-5px);
        border-color: #EA580C;
        box-shadow: 0 14px 24px -5px rgba(234, 88, 12, 0.14);
    }
    
    .apunte-container {
        background-color: white;
        border-left: 6px solid #EA580C;
        padding: 26px;
        border-radius: 14px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.03);
        line-height: 1.7;
    }
    
    .badge-dias {
        background: #FEF3C7; color: #92400E; border: 1px solid #FDE68A;
        padding: 3px 8px; border-radius: 10px; font-size: 11px; font-weight: 700;
        display: inline-block; margin-top: 4px;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #EA580C 0%, #C2410C 100%);
        color: white; border-radius: 10px; border: none; font-weight: 600; padding: 10px 20px;
    }
    .stButton>button:hover { opacity: 0.92; color: white; }
    </style>
""", unsafe_allow_html=True)

# --- CLIENTE GEMINI ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)
except Exception:
    client = None

CARPETA_DATOS = Path("Campus_Familiar_Datos")
CARPETA_DATOS.mkdir(exist_ok=True)

# --- ESTADO DE SESIÓN ---
if "usuario_activo" not in st.session_state:
    st.session_state.usuario_activo = None
if "asig_actual" not in st.session_state:
    st.session_state.asig_actual = None
if "seccion_activa" not in st.session_state:
    st.session_state.seccion_activa = "mosaico"
if "xp" not in st.session_state:
    st.session_state.xp = 250

# --- FUNCIONES DE JSON ---
def leer_json(ruta_f, default):
    if ruta_f.exists():
        try:
            with open(ruta_f, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default

def escribir_json(ruta_f, data):
    with open(ruta_f, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def obtener_archivos_materia(ruta_asig):
    excluidos = ["apuntes_guardados.txt", "metadata.json", "examenes_historial.json", "podcast.mp3", "guion_podcast.txt"]
    return [f for f in ruta_asig.glob("*") if f.is_file() and f.name not in excluidos]

# --- GENERADOR MAESTRO DE PDF ---
def generar_pdf_documento(titulo_doc, subtitulo_doc, contenido_markdown):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    
    t_style = ParagraphStyle('DocTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=colors.HexColor('#EA580C'), spaceAfter=4)
    sub_style = ParagraphStyle('DocSub', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=13, textColor=colors.HexColor('#475569'), spaceAfter=12)
    h1_style = ParagraphStyle('H1', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=13, leading=17, textColor=colors.HexColor('#0F172A'), spaceBefore=10, spaceAfter=4)
    h2_style = ParagraphStyle('H2', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=colors.HexColor('#1E293B'), spaceBefore=7, spaceAfter=3)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=13, textColor=colors.HexColor('#334155'), spaceAfter=4)
    
    story = [
        Paragraph(titulo_doc, t_style),
        Paragraph(subtitulo_doc, sub_style),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#EA580C'), spaceAfter=10)
    ]
    
    for linea in contenido_markdown.split("\n"):
        l = linea.strip()
        if not l:
            story.append(Spacer(1, 3))
            continue
        txt = l.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        if txt.startswith("# "):
            story.append(Paragraph(txt.replace("# ", ""), h1_style))
        elif txt.startswith("## ") or txt.startswith("### "):
            story.append(Paragraph(txt.lstrip("#").strip(), h2_style))
        elif txt.startswith("- ") or txt.startswith("* "):
            story.append(Paragraph(f"• {txt[2:]}", body_style))
        else:
            story.append(Paragraph(txt, body_style))
            
    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()

# --- PROCESAMIENTO ESTILO NOTEBOOKLM (CON ESPERA ACTIVA REAL) ---
def procesar_archivos_notebooklm(rutas_archivos, barra_progreso, texto_estado):
    archivos_remotos = []
    total = len(rutas_archivos)
    
    for i, r in enumerate(rutas_archivos):
        if r.suffix.lower() in [".mp3", ".m4a", ".wav", ".pdf"]:
            texto_estado.info(f"📤 Subiendo a la nube de estudio: {r.name} ({i+1}/{total})...")
            barra_progreso.progress(int(((i + 0.5) / total) * 50))
            
            sub = client.files.upload(file=str(r))
            
            # ESPERA ACTIVA: Si es audio o PDF pesado, esperar a que Gemini termine de indexarlo
            while sub.state and sub.state.name == "PROCESSING":
                texto_estado.info(f"⏳ Indexando y transcribiendo audio/documento: {r.name}...")
                time.sleep(3)
                sub = client.files.get(name=sub.name)
                
            archivos_remotos.append(sub)
            barra_progreso.progress(int(((i + 1) / total) * 50))
            
    return archivos_remotos

def obtener_icono_asig(nombre):
    n = nombre.lower()
    if any(k in n for k in ["geo", "tierra"]): return "🌍"
    if any(k in n for k in ["historia", "arte", "roma", "antigua", "medieval"]): return "🏛️"
    if any(k in n for k in ["lengua", "literatura", "idioma", "latin"]): return "📖"
    if any(k in n for k in ["mate", "algebra", "calculo", "fisica"]): return "📐"
    if any(k in n for k in ["bio", "ciencias", "naturales", "quimica", "salud"]): return "🧬"
    if any(k in n for k in ["filo", "etica", "pensamiento"]): return "💡"
    if any(k in n for k in ["ingles", "frances"]): return "🗣️"
    return "📚"

def render_chopi_header():
    nivel_chopi = (st.session_state.xp // 100) + 1
    col_c1, col_c2 = st.columns([5, 1])
    with col_c1:
        st.markdown(f"""
            <div class="chopi-header">
                <div class="chopi-avatar">🐕‍🦺</div>
                <div>
                    <h3 style="margin:0; color: #F8FAFC;">Chopi - Tu Compañero Patterdale Terrier</h3>
                    <p style="margin:2px 0 0 0; color: #94A3B8; font-size: 13px;">
                        Nivel <b>{nivel_chopi}</b> • XP: <b>{st.session_state.xp}</b> | Sistema tipo NotebookLM listo para iPad, Mac y PC.
                    </p>
                </div>
            </div>
        """, unsafe_allow_html=True)
    with col_c2:
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        if st.button("🍖 Premiar"):
            st.session_state.xp += 20
            st.balloons()
            st.rerun()

# ==============================================================================
# 1. PANTALLA PRINCIPAL (SELECCIÓN Y CONFIGURACIÓN DE USUARIO)
# ==============================================================================
if st.session_state.usuario_activo is None:
    render_chopi_header()
    
    st.markdown("""
        <div style="background: white; border: 1px solid #E2E8F0; border-radius: 18px; padding: 24px; margin-bottom: 22px;">
            <h1 style="margin:0 0 6px 0; color: #0F172A; font-size: 26px;">🎓 Campus Educativo Familiar & VIU</h1>
            <p style="margin:0; color: #475569; font-size: 14.5px;">
                Espacio de estudio adaptado: Universidad (VIU) y Currículo Oficial de Castilla y León (BOCYL).
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    tab_bienv, tab_tut, tab_admin = st.tabs(["🚀 Capacidades", "📖 Tutorial Rápido", "⚙️ Gestión de Usuarios"])
    
    with tab_bienv:
        c1, c2 = st.columns(2)
        c1.markdown("""
        #### 🎓 Para la Universidad (VIU)
        * **Audios de 2 horas sin bloqueos:** Indexación directa tipo NotebookLM.
        * **Fidelidad Absoluta:** Modo riguroso estricto centrado en tus clases.
        * **Cuadernos, Podcasts y Exámenes en PDF y MP3.**
        """)
        c2.markdown("""
        #### 🎒 Colegio e Instituto (Castilla y León)
        * **Primaria, ESO y Bachillerato:** Basado en el currículo normativo (BOCYL / LOMLOE).
        * **Bachillerato por ramas:** Ciencias, Humanidades o Salud.
        * **Sin necesidad de escanear libros físicos.**
        """)
        
    with tab_tut:
        st.markdown("""
        1. **Selecciona tu Perfil** abajo.
        2. **Entra a tu Asignatura** y navega por el mosaico interactivo.
        3. Sube tus audios o PDFs en **📂 Fuentes y Materiales**.
        4. Entra a **✨ Cuaderno de Estudio** para generar tus apuntes con streaming y descargarlos en **PDF**.
        5. Escucha el **🎙️ Podcast en MP3** o haz simulacros en **🎯 Estudio Activo**.
        """)
        
    with tab_admin:
        col_n1, col_n2, col_n3 = st.columns([2, 2, 1])
        with col_n1:
            nuevo_n = st.text_input("Nombre:")
        with col_n2:
            nuevo_nv = st.selectbox("Etapa:", ["Universidad", "Bachillerato (Castilla y León)", "ESO (Castilla y León)", "Primaria (Castilla y León)"])
            rama = "General"
            if "Bachillerato" in nuevo_nv:
                rama = st.selectbox("Rama:", ["Ciencias y Tecnología", "Humanidades y Ciencias Sociales", "Ciencias de la Salud"])
        with col_n3:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("➕ Crear", use_container_width=True):
                if nuevo_n:
                    r = CARPETA_DATOS / nuevo_n
                    r.mkdir(exist_ok=True)
                    escribir_json(r / "config.json", {"nivel": nuevo_nv, "rama_bach": rama})
                    st.rerun()

    st.markdown("---")
    st.subheader("👤 Elige quién va a estudiar hoy:")
    perfiles = [d.name for d in CARPETA_DATOS.iterdir() if d.is_dir()]
    if perfiles:
        cols_usr = st.columns(max(len(perfiles), 3))
        for i, perf in enumerate(perfiles):
            r_perf = CARPETA_DATOS / perf
            cfg_p = leer_json(r_perf / "config.json", {"nivel": "Universidad", "rama_bach": ""})
            nv_p = cfg_p.get("nivel", "Universidad")
            rama_txt = f"({cfg_p.get('rama_bach', '')})" if "Bachillerato" in nv_p else ""
            with cols_usr[i % len(cols_usr)]:
                st.markdown(f"""
                    <div style="background: white; border: 2px solid #E2E8F0; border-radius: 16px; padding: 18px; text-align: center;">
                        <div style="font-size: 36px;">🧑‍🎓</div>
                        <h4 style="margin: 4px 0; color: #0F172A;">{perf}</h4>
                        <p style="margin:0 0 10px 0; color: #64748B; font-size: 12px;">{nv_p} {rama_txt}</p>
                    </div>
                """, unsafe_allow_html=True)
                col_b1, col_b2 = st.columns([3, 1])
                if col_b1.button("Entrar", key=f"sel_u_{perf}", use_container_width=True):
                    st.session_state.usuario_activo = perf
                    st.session_state.asig_actual = None
                    st.session_state.seccion_activa = "mosaico"
                    st.rerun()
                if col_b2.button("🗑️", key=f"del_u_{perf}"):
                    import shutil
                    shutil.rmtree(r_perf)
                    st.rerun()

# ==============================================================================
# 2. ESPACIO PRIVADO DEL ESTUDIANTE
# ==============================================================================
else:
    render_chopi_header()
    usr_actual = st.session_state.usuario_activo
    ruta_usr = CARPETA_DATOS / usr_actual
    config_usr = leer_json(ruta_usr / "config.json", {"nivel": "Universidad", "rama_bach": "Ciencias y Tecnología"})
    nivel_estudiante = config_usr.get("nivel", "Universidad")
    rama_bach = config_usr.get("rama_bach", "Ciencias y Tecnología")
    
    if "Primaria" in nivel_estudiante:
        texto_etapa = "🏫 Tus Asignaturas del Colegio"
    elif any(k in nivel_estudiante for k in ["ESO", "Bachillerato"]):
        texto_etapa = "🎒 Tus Asignaturas del Instituto"
    else:
        texto_etapa = "🎓 Tus Asignaturas de la Universidad (VIU)"

    with st.sidebar:
        st.markdown(f"### 👤 {usr_actual}")
        st.caption(f"**{nivel_estudiante}** {f'({rama_bach})' if 'Bachillerato' in nivel_estudiante else ''}")
        if st.button("🚪 Cambiar de Estudiante", use_container_width=True):
            st.session_state.usuario_activo = None
            st.session_state.asig_actual = None
            st.session_state.seccion_activa = "mosaico"
            st.rerun()

    # --------------------------------------------------------------------------
    # 2.1 LISTADO DE ASIGNATURAS
    # --------------------------------------------------------------------------
    if st.session_state.asig_actual is None:
        st.markdown(f"""
            <div style="background: white; border: 1px solid #E2E8F0; border-radius: 16px; padding: 20px; margin-bottom: 20px;">
                <h2 style="margin: 0 0 4px 0; color: #0F172A;">{texto_etapa}</h2>
                <p style="margin:0; color: #64748B;">Estudiante: <b>{usr_actual}</b> {f'— Modalidad: {rama_bach}' if 'Bachillerato' in nivel_estudiante else ''}</p>
            </div>
        """, unsafe_allow_html=True)
        
        col_a1, col_a2 = st.columns([3, 1])
        with col_a1:
            nom_asig = st.text_input("Nueva Asignatura:", placeholder="Ej. Historia Contemporánea, Geografía 2º ESO...", label_visibility="collapsed")
        with col_a2:
            if st.button("➕ Añadir Asignatura", use_container_width=True):
                if nom_asig:
                    (ruta_usr / nom_asig).mkdir(exist_ok=True)
                    st.rerun()
                    
        asigs = [d.name for d in ruta_usr.iterdir() if d.is_dir()]
        if not asigs:
            st.info("No hay asignaturas creadas todavía. Añade una arriba para empezar.")
        else:
            cols_as = st.columns(3)
            for idx, a_name in enumerate(asigs):
                r_as = ruta_usr / a_name
                ic = obtener_icono_asig(a_name)
                meta = leer_json(r_as / "metadata.json", {})
                historial_ex = leer_json(r_as / "examenes_historial.json", [])
                
                nota_media_txt = ""
                if historial_ex:
                    media = sum([x["nota"] for x in historial_ex]) / len(historial_ex)
                    nota_media_txt = f"<div style='color: #059669; font-size: 11px; font-weight: bold;'>📊 Media: {media:.2f} / 10</div>"
                
                badge_examen = ""
                if meta.get("fecha_examen"):
                    f_ex = datetime.strptime(meta["fecha_examen"], "%Y-%m-%d").date()
                    delta = (f_ex - date.today()).days
                    if delta > 0:
                        badge_examen = f'<div class="badge-dias">⏳ Examen en {delta} días</div>'
                    elif delta == 0:
                        badge_examen = '<div class="badge-dias" style="background:#FEE2E2; color:#991B1B;">🔥 ¡Examen HOY!</div>'
                
                with cols_as[idx % 3]:
                    st.markdown(f"""
                        <div class="mosaic-card">
                            <div>
                                <div style="font-size: 38px;">{ic}</div>
                                <h4 style="margin: 6px 0 2px 0; color: #0F172A;">{a_name}</h4>
                                {badge_examen}
                                {nota_media_txt}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                    col_b1, col_b2 = st.columns([3, 1])
                    if col_b1.button("📂 Entrar", key=f"entrar_{a_name}", use_container_width=True):
                        st.session_state.asig_actual = a_name
                        st.session_state.seccion_activa = "mosaico"
                        st.rerun()
                    if col_b2.button("🗑️", key=f"del_a_{a_name}"):
                        import shutil
                        shutil.rmtree(r_as)
                        st.rerun()

    # --------------------------------------------------------------------------
    # 2.2 DENTRO DE LA ASIGNATURA: MOSAICO TIPO NOTEBOOKLM / STUDYFETCH
    # --------------------------------------------------------------------------
    else:
        asig_sel = st.session_state.asig_actual
        ruta_asig = ruta_usr / asig_sel
        icono_materia = obtener_icono_asig(asig_sel)
        meta_asig = leer_json(ruta_asig / "metadata.json", {})
        
        # Barra superior de la Asignatura
        col_nav1, col_nav2 = st.columns([1, 3])
        with col_nav1:
            if st.session_state.seccion_activa != "mosaico":
                if st.button("⬅️ Panel Principal de Asignatura"):
                    st.session_state.seccion_activa = "mosaico"
                    st.rerun()
            else:
                if st.button("⬅️ Mis Asignaturas"):
                    st.session_state.asig_actual = None
                    st.rerun()
                    
        with col_nav2:
            f_actual = None
            if meta_asig.get("fecha_examen"):
                f_actual = datetime.strptime(meta_asig["fecha_examen"], "%Y-%m-%d").date()
            with st.popover("📅 Fecha de Examen y Cuenta Atrás"):
                nueva_f = st.date_input("Fecha del próximo examen:", value=f_actual if f_actual else date.today())
                if st.button("Guardar Fecha"):
                    meta_asig["fecha_examen"] = str(nueva_f)
                    escribir_json(ruta_asig / "metadata.json", meta_asig)
                    st.rerun()

        st.markdown(f"## {icono_materia} {asig_sel}")
        if meta_asig.get("fecha_examen"):
            f_ex = datetime.strptime(meta_asig["fecha_examen"], "%Y-%m-%d").date()
            delta = (f_ex - date.today()).days
            if delta >= 0:
                st.info(f"⏳ **Cuenta atrás:** Faltan **{delta} días** para el examen ({f_ex.strftime('%d/%m/%Y')}).")

        # ----------------------------------------------------------------------
        # MOSAICO PRINCIPAL DE LA ASIGNATURA
        # ----------------------------------------------------------------------
        if st.session_state.seccion_activa == "mosaico":
            st.markdown("### 🎛️ Espacio de Estudio y Fuentes")
            
            c_m1, c_m2, c_m3 = st.columns(3)
            
            with c_m1:
                st.markdown("""
                    <div class="mosaic-card">
                        <div>
                            <div style="font-size: 38px;">📂</div>
                            <h3 style="margin: 6px 0; color: #0F172A;">Materiales y Fuentes</h3>
                            <p style="color: #64748B; font-size: 13px;">Sube audios de 2h, libros en PDF o enlaces de clase.</p>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button("Abrir Fuentes", key="btn_mos_mat", use_container_width=True):
                    st.session_state.seccion_activa = "materiales"
                    st.rerun()

            with c_m2:
                st.markdown("""
                    <div class="mosaic-card">
                        <div>
                            <div style="font-size: 38px;">✨</div>
                            <h3 style="margin: 6px 0; color: #0F172A;">Cuaderno de Estudio</h3>
                            <p style="color: #64748B; font-size: 13px;">Apuntes dinámicos estructurados con descarga en PDF.</p>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button("Abrir Cuaderno", key="btn_mos_ap", use_container_width=True):
                    st.session_state.seccion_activa = "apuntes"
                    st.rerun()

            with c_m3:
                st.markdown("""
                    <div class="mosaic-card">
                        <div>
                            <div style="font-size: 38px;">🎙️</div>
                            <h3 style="margin: 6px 0; color: #0F172A;">Lección en Podcast</h3>
                            <p style="color: #64748B; font-size: 13px;">Explicación narrada en audio MP3 para repasar donde quieras.</p>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button("Abrir Podcast", key="btn_mos_pod", use_container_width=True):
                    st.session_state.seccion_activa = "podcast"
                    st.rerun()

            c_m4, c_m5, c_m6 = st.columns(3)
            
            with c_m4:
                st.markdown("""
                    <div class="mosaic-card">
                        <div>
                            <div style="font-size: 38px;">🎯</div>
                            <h3 style="margin: 6px 0; color: #0F172A;">Estudio Activo / Exámenes</h3>
                            <p style="color: #64748B; font-size: 13px;">Test interactivos, preguntas de desarrollo y PDF.</p>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button("Hacer Examen", key="btn_mos_ex", use_container_width=True):
                    st.session_state.seccion_activa = "examenes"
                    st.rerun()

            with c_m5:
                st.markdown("""
                    <div class="mosaic-card">
                        <div>
                            <div style="font-size: 38px;">📑</div>
                            <h3 style="margin: 6px 0; color: #0F172A;">Auditor de Trabajos</h3>
                            <p style="color: #64748B; font-size: 13px;">Corrección con rúbrica o criterios universitarios 0-10.</p>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button("Evaluar Trabajo", key="btn_mos_trab", use_container_width=True):
                    st.session_state.seccion_activa = "trabajos"
                    st.rerun()

            with c_m6:
                st.markdown("""
                    <div class="mosaic-card">
                        <div>
                            <div style="font-size: 38px;">🤖</div>
                            <h3 style="margin: 6px 0; color: #0F172A;">Tutor Visual Interactivo</h3>
                            <p style="color: #64748B; font-size: 13px;">Esquemas, mapas conceptuales y exportación en PDF.</p>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                if st.button("Consultar Tutor", key="btn_mos_tut", use_container_width=True):
                    st.session_state.seccion_activa = "tutor"
                    st.rerun()

        # ----------------------------------------------------------------------
        # SECCIONES ESPECÍFICAS
        # ----------------------------------------------------------------------
        
        # 1. MATERIALES Y FUENTES
        elif st.session_state.seccion_activa == "materiales":
            st.subheader("📂 Fuentes y Materiales de la Asignatura")
            st.caption("Sube grabaciones de clase en MP3/M4A de hasta 2 horas o documentos PDF.")
            
            subidos = st.file_uploader("Añadir nuevos archivos a las fuentes:", type=["pdf", "mp3", "m4a", "wav"], accept_multiple_files=True)
            if subidos:
                for arc in subidos:
                    with open(ruta_asig / arc.name, "wb") as f:
                        f.write(arc.getbuffer())
                st.success("¡Archivos guardados en el campus!")
                st.rerun()
                
            archivos_actuales = obtener_archivos_materia(ruta_asig)
            if archivos_actuales:
                st.markdown("#### 📄 Documentos y Audios Almacenados:")
                for f in archivos_actuales:
                    cf1, cf2 = st.columns([4, 1])
                    tam = round(f.stat().st_size / (1024 * 1024), 2)
                    cf1.text(f"• {f.name} ({tam} MB)")
                    if cf2.button("🗑️", key=f"delf_{f.name}"):
                        f.unlink()
                        st.rerun()
            else:
                st.info("No hay archivos subidos todavía.")

        # 2. CUADERNO DE ESTUDIO (APUNTES DINÁMICOS CON STREAMING)
        elif st.session_state.seccion_activa == "apuntes":
            st.subheader("✨ Cuaderno de Estudio Inteligente")
            f_apuntes = ruta_asig / "apuntes_guardados.txt"
            
            archivos_asig = obtener_archivos_materia(ruta_asig)
            
            c_btn1, c_btn2 = st.columns([2, 1])
            with c_btn1:
                if st.button("🚀 Generar / Actualizar Apuntes con Streaming"):
                    if client:
                        barra = st.progress(0)
                        txt_est = st.empty()
                        
                        # Subida con espera activa estilo NotebookLM
                        remotos = procesar_archivos_notebooklm(archivos_asig, barra, txt_est)
                        
                        txt_est.info("✍️ Gemini está redactando tus apuntes en tiempo real...")
                        barra.progress(70)
                        
                        if "Bachillerato" in nivel_estudiante:
                            ctx = f"ESTUDIANTE DE BACHILLERATO ({rama_bach}) - Currículo Oficial de Castilla y León (BOCYL / LOMLOE)."
                        elif "Castilla y León" in nivel_estudiante:
                            ctx = f"ESTUDIANTE ESCOLAR ({nivel_estudiante}) - Currículo Oficial de Castilla y León (BOCYL / LOMLOE)."
                        else:
                            ctx = "ESTUDIANTE UNIVERSITARIO (VIU - Grado en Historia). Rigor historiográfico y conceptual. Sintetiza minuciosamente los audios y documentos."

                        prompt = f"""
                        {ctx}
                        Genera unos apuntes dinámicos, estructurados, visuales y completos para la asignatura: '{asig_sel}'.
                        Sintetiza minuciosamente todos los archivos de audio y documentos adjuntos.
                        Estructura con títulos jerárquicos (#, ##), tablas comparativas, cronologías, resúmenes clave y conceptos destacados.
                        """
                        
                        # Generación con Streaming fluido
                        res_stream = client.models.generate_content_stream(
                            model='gemini-3.5-flash',
                            contents=[prompt] + remotos
                        )
                        
                        texto_completo = ""
                        contenedor_texto = st.empty()
                        for chunk in res_stream:
                            if chunk.text:
                                texto_completo += chunk.text
                                contenedor_texto.markdown(texto_completo)
                                
                        with open(f_apuntes, "w", encoding="utf-8") as f:
                            f.write(texto_completo)
                            
                        barra.progress(100)
                        txt_est.success("¡Apuntes generados y guardados con éxito!")
                        st.session_state.xp += 35
                        st.rerun()
                        
            if f_apuntes.exists():
                with open(f_apuntes, "r", encoding="utf-8") as f:
                    txt_ap = f.read()
                    
                with c_btn2:
                    subtit = f"{nivel_estudiante} ({rama_bach})" if "Bachillerato" in nivel_estudiante else nivel_estudiante
                    pdf_bytes = generar_pdf_documento(f"Apuntes: {asig_sel}", subtit, txt_ap)
                    st.download_button(
                        label="📄 Descargar Apuntes en PDF",
                        data=pdf_bytes,
                        file_name=f"Apuntes_{asig_sel}.pdf",
                        mime="application/pdf",
                        use_container_width=True
                    )
                    
                st.markdown(f"""
                    <div class="apunte-container">
                        {txt_ap}
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.info("Pulsa el botón de arriba para comenzar a generar los apuntes.")

        # 3. LECCIÓN EN PODCAST (AUDIO MP3)
        elif st.session_state.seccion_activa == "podcast":
            st.subheader("🎙️ Lección en Podcast Académico")
            f_podcast_audio = ruta_asig / "podcast.mp3"
            f_podcast_guion = ruta_asig / "guion_podcast.txt"
            
            duracion_pod = st.select_slider("Estilo de narración:", options=["Resumen Rápido (3-4 min)", "Lección Completa (8-10 min)"])
            
            if st.button("🎧 Generar Podcast en MP3"):
                if client:
                    barra_p = st.progress(0)
                    txt_p = st.empty()
                    archivos = obtener_archivos_materia(ruta_asig)
                    remotos = procesar_archivos_notebooklm(archivos, barra_p, txt_p)
                    
                    txt_p.info("🎙️ Redactando guion pedagógico...")
                    barra_p.progress(60)
                    
                    prompt_pod = f"""
                    Actúa como el locutor de un podcast educativo de alto nivel.
                    Asignatura: {asig_sel}. Nivel: {nivel_estudiante} {f'({rama_bach})' if 'Bachillerato' in nivel_estudiante else ''}.
                    Estilo: {duracion_pod}.
                    
                    Redacta el guion hablado completo, en primera persona, sin acotaciones teatrales, con tono ameno pero riguroso.
                    """
                    res_pod = client.models.generate_content(
                        model='gemini-3.5-flash',
                        contents=[prompt_pod] + remotos
                    )
                    guion_texto = res_pod.text
                    
                    with open(f_podcast_guion, "w", encoding="utf-8") as f:
                        f.write(guion_texto)
                        
                    txt_p.info("🔊 Grabando voz en español...")
                    barra_p.progress(85)
                    
                    tts = gTTS(text=guion_texto, lang='es', tld='es')
                    tts.save(str(f_podcast_audio))
                    
                    barra_p.progress(100)
                    txt_p.success("¡Podcast generado!")
                    st.session_state.xp += 35
                    st.rerun()
                    
            if f_podcast_audio.exists():
                st.markdown("### 📻 Reproductor de Audio:")
                with open(f_podcast_audio, "rb") as audio_file:
                    audio_bytes = audio_file.read()
                st.audio(audio_bytes, format='audio/mp3')
                
                st.download_button(
                    label="📥 Descargar Podcast (.MP3)",
                    data=audio_bytes,
                    file_name=f"Podcast_{asig_sel}.mp3",
                    mime="audio/mp3",
                    use_container_width=True
                )
                
                if f_podcast_guion.exists():
                    with st.expander("📜 Ver Guion del Podcast"):
                        with open(f_podcast_guion, "r", encoding="utf-8") as f:
                            st.write(f.read())

        # 4. ESTUDIO ACTIVO / EXÁMENES INTERACTIVOS Y PDF
        elif st.session_state.seccion_activa == "examenes":
            st.subheader("🎯 Creador de Exámenes (Test, Desarrollo y PDF)")
            
            historial_ex = leer_json(ruta_asig / "examenes_historial.json", [])
            if historial_ex:
                media_total = sum([x["nota"] for x in historial_ex]) / len(historial_ex)
                st.success(f"📊 **Nota Media Acumulada: {media_total:.2f} / 10** ({len(historial_ex)} exámenes realizados)")
                
            col_cfg1, col_cfg2 = st.columns(2)
            with col_cfg1:
                n_test = st.slider("Preguntas Tipo Test:", 0, 25, 5)
            with col_cfg2:
                n_redaccion = st.slider("Preguntas de Desarrollo / Redacción:", 0, 10, 2)
                
            archivos_disponibles = [f.name for f in obtener_archivos_materia(ruta_asig)]
            elegir_todos = st.checkbox("✅ Incluir todos los materiales disponibles", value=True)
            materiales_sel = []
            if not elegir_todos and archivos_disponibles:
                for arc_n in archivos_disponibles:
                    if st.checkbox(arc_n, value=False, key=f"mat_sel_{arc_n}"):
                        materiales_sel.append(arc_n)
            else:
                materiales_sel = archivos_disponibles
                
            if st.button("🚀 Lanzar Nuevo Examen"):
                if client:
                    with st.spinner("Redactando examen estructurado..."):
                        prompt_json = f"""
                        Genera un examen para la asignatura: {asig_sel}.
                        Nivel: {nivel_estudiante} {f'({rama_bach})' if 'Bachillerato' in nivel_estudiante else ''}.
                        Materiales: {', '.join(materiales_sel) if materiales_sel else 'Currículo oficial'}.
                        Configuración: {n_test} preguntas test, {n_redaccion} preguntas desarrollo.
                        
                        Devuelve EXCLUSIVAMENTE un objeto JSON con:
                        {{
                          "preguntas_test": [
                            {{
                              "pregunta": "¿Texto pregunta test?",
                              "opciones": ["A", "B", "C", "D"],
                              "correcta": 0,
                              "explicacion": "Explicación de la respuesta."
                            }}
                          ],
                          "preguntas_desarrollo": [
                            {{
                              "enunciado": "Enunciado del tema de desarrollo.",
                              "criterios_correccion": "Conceptos clave requeridos."
                            }}
                          ]
                        }}
                        """
                        try:
                            res = client.models.generate_content(model='gemini-3.5-flash', contents=prompt_json)
                            raw_text = res.text.strip()
                            if raw_text.startswith("```json"): raw_text = raw_text[7:]
                            if raw_text.endswith("```"): raw_text = raw_text[:-3]
                            data_ex = json.loads(raw_text.strip())
                            st.session_state[f"examen_activo_{asig_sel}"] = data_ex
                            st.session_state[f"respuestas_usuario_{asig_sel}"] = {}
                            st.session_state[f"corregido_{asig_sel}"] = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al generar examen: {e}")

            if f"examen_activo_{asig_sel}" in st.session_state:
                examen = st.session_state[f"examen_activo_{asig_sel}"]
                tests = examen.get("preguntas_test", [])
                desarrollos = examen.get("preguntas_desarrollo", [])
                
                texto_examen_markdown = f"# Examen Oficial: {asig_sel}\n\n"
                if tests:
                    texto_examen_markdown += "## Parte 1: Preguntas Tipo Test\n"
                    for i, p in enumerate(tests):
                        texto_examen_markdown += f"\n**{i+1}. {p['pregunta']}**\n"
                        for opt in p['opciones']: texto_examen_markdown += f"- {opt}\n"
                if desarrollos:
                    texto_examen_markdown += "\n## Parte 2: Preguntas de Desarrollo\n"
                    for j, d in enumerate(desarrollos):
                        texto_examen_markdown += f"\n**Tema {j+1}:** {d['enunciado']}\n"
                
                pdf_examen_bytes = generar_pdf_documento(f"Examen: {asig_sel}", f"Nivel: {nivel_estudiante}", texto_examen_markdown)
                st.download_button(
                    label="📄 Descargar este Examen en PDF",
                    data=pdf_examen_bytes,
                    file_name=f"Examen_{asig_sel}.pdf",
                    mime="application/pdf"
                )
                st.markdown("---")
                
                if tests:
                    st.markdown("### 📝 Parte 1: Preguntas Tipo Test")
                    for i, p in enumerate(tests):
                        st.markdown(f"**Pregunta {i+1}: {p['pregunta']}**")
                        st.session_state[f"respuestas_usuario_{asig_sel}"][i] = st.radio(
                            f"Respuesta {i+1}:",
                            options=list(range(len(p["opciones"]))),
                            format_func=lambda opt_idx: p["opciones"][opt_idx],
                            key=f"radio_p_{asig_sel}_{i}",
                            label_visibility="collapsed"
                        )
                        st.markdown("---")
                        
                if desarrollos:
                    st.markdown("### ✍️ Parte 2: Preguntas de Desarrollo")
                    for j, d in enumerate(desarrollos):
                        st.markdown(f"**Tema/Pregunta {j+1}:** {d['enunciado']}")
                        st.text_area(f"Escribe tu redacción ({j+1}):", height=120, key=f"redaccion_{asig_sel}_{j}")
                        with st.expander("🔍 Ver Criterios de Corrección"):
                            st.info(d["criterios_correccion"])
                        st.markdown("---")
                        
                if tests and st.button("🏁 Corregir Parte Test"):
                    st.session_state[f"corregido_{asig_sel}"] = True
                    
                if st.session_state.get(f"corregido_{asig_sel}", False) and tests:
                    aciertos = 0
                    st.markdown("## 📊 Corrección Razonada")
                    for i, p in enumerate(tests):
                        resp_u = st.session_state[f"respuestas_usuario_{asig_sel}"].get(i, None)
                        if resp_u == p["correcta"]:
                            aciertos += 1
                            st.success(f"✅ **Pregunta {i+1}: ¡Correcta!**\n\nTu respuesta: {p['opciones'][resp_u]}\n\n💡 {p['explicacion']}")
                        else:
                            st.error(f"❌ **Pregunta {i+1}: Fallo**\n\nTu respuesta: {p['opciones'][resp_u] if resp_u is not None else 'Sin responder'}\n\nRespuesta correcta: **{p['opciones'][p['correcta']]}**\n\n💡 **¿Por qué has fallado?:** {p['explicacion']}")
                            
                    nota_obtenida = round((aciertos / len(tests)) * 10, 2)
                    st.markdown(f"### 🏆 Calificación Test: **{nota_obtenida} / 10**")
                    
                    if st.button("💾 Guardar Nota en Expediente"):
                        historial_ex.append({"fecha": str(date.today()), "nota": nota_obtenida, "preguntas": len(tests)})
                        escribir_json(ruta_asig / "examenes_historial.json", historial_ex)
                        st.session_state.xp += int(nota_obtenida * 5)
                        st.success("Nota guardada.")
                        del st.session_state[f"examen_activo_{asig_sel}"]
                        st.rerun()

        # 5. AUDITOR DE TRABAJOS
        elif st.session_state.seccion_activa == "trabajos":
            st.subheader("📑 Corrector y Evaluador de Trabajos y Ensayos")
            trabajo_texto = st.text_area("Pega tu trabajo o ensayo:", height=200)
            rubrica_usr = st.text_area("Rúbrica específica (opcional):", placeholder="Si lo dejas en blanco, aplicará criterios universitarios de Grado de Historia...")
            
            if st.button("🔍 Evaluar Trabajo"):
                if trabajo_texto and client:
                    with st.spinner("Evaluando con rigor académico..."):
                        prompt_eval = f"""
                        Evalúa este trabajo para {asig_sel} (Nivel: {nivel_estudiante}):
                        {f'Rúbrica: {rubrica_usr}' if rubrica_usr.strip() else 'Criterios de Grado de Historia: rigor historiográfico, fuentes, coherencia y sintaxis.'}
                        
                        Trabajo:
                        \"\"\"{trabajo_texto}\"\"\"
                        
                        Estructura: 1. Calificación Final (0-10), 2. Puntos Fuertes, 3. Errores, 4. Sugerencias de Redacción.
                        """
                        res_eval = client.models.generate_content(model='gemini-3.5-flash', contents=prompt_eval)
                        st.session_state[f"evaluacion_{asig_sel}"] = res_eval.text
                        st.session_state.xp += 40
                        st.rerun()
                        
            if f"evaluacion_{asig_sel}" in st.session_state:
                st.markdown("---")
                st.markdown(st.session_state[f"evaluacion_{asig_sel}"])

        # 6. TUTOR VISUAL
        elif st.session_state.seccion_activa == "tutor":
            st.subheader("🤖 Tutor Visual Interactivo (Con Descarga PDF)")
            duda = st.text_input("Formula tu consulta académica:")
            
            if duda and client:
                with st.spinner("Preparando explicación visual..."):
                    prompt_tutor_visual = f"""
                    Actúa como docente experto en {asig_sel} para {nivel_estudiante} {f'({rama_bach})' if 'Bachillerato' in nivel_estudiante else ''}.
                    Pregunta: "{duda}"
                    INSTRUCCIONES VISUALES: 1. Gráfica y visual, 2. Esquemas o cajas de conceptos, 3. Tablas comparativas o líneas de tiempo, 4. '💡 Ideas Clave para Recordar'.
                    """
                    res_tut = client.models.generate_content(model='gemini-3.5-flash', contents=prompt_tutor_visual)
                    st.session_state[f"tutor_resp_{asig_sel}"] = res_tut.text
                    st.session_state[f"tutor_duda_{asig_sel}"] = duda
                    
            if f"tutor_resp_{asig_sel}" in st.session_state:
                st.markdown("---")
                pdf_tutor_bytes = generar_pdf_documento(
                    f"Consulta Tutor: {asig_sel}",
                    f"Pregunta: {st.session_state.get(f'tutor_duda_{asig_sel}', '')}",
                    st.session_state[f"tutor_resp_{asig_sel}"]
                )
                st.download_button(
                    label="📄 Descargar esta Explicación en PDF",
                    data=pdf_tutor_bytes,
                    file_name=f"Tutor_{asig_sel}.pdf",
                    mime="application/pdf"
                )
                st.markdown(f"""
                    <div class="apunte-container">
                        {st.session_state[f"tutor_resp_{asig_sel}"]}
                    </div>
                """, unsafe_allow_html=True)
