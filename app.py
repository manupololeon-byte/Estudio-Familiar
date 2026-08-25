import streamlit as st
import os
import json
import io
from datetime import datetime, date
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from google import genai

# ReportLab para PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.units import cm

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(
    page_title="Campus Educativo Familiar & VIU",
    page_icon="🐕‍🦺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- ESTILOS MODERNOS CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    .main { background-color: #F8FAFC; }
    
    @keyframes petFloat {
        0%, 100% { transform: translateY(0px) rotate(0deg); }
        50% { transform: translateY(-5px) rotate(1deg); }
    }
    
    .chopi-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        border: 1px solid #334155;
        border-radius: 20px;
        padding: 20px 26px;
        color: white;
        display: flex;
        align-items: center;
        gap: 18px;
        box-shadow: 0 10px 25px -5px rgba(15, 23, 42, 0.15);
        margin-bottom: 22px;
    }
    
    .chopi-avatar {
        font-size: 48px;
        background: #1E293B;
        border: 2px solid #F59E0B;
        border-radius: 50%;
        padding: 8px 12px;
        animation: petFloat 4s ease-in-out infinite;
    }
    
    .hero-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 18px;
        padding: 26px;
        margin-bottom: 22px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.04);
    }
    
    .user-badge-card {
        background: white;
        border: 2px solid #E2E8F0;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        transition: all 0.25s ease;
    }
    .user-badge-card:hover {
        border-color: #EA580C;
        transform: translateY(-4px);
        box-shadow: 0 10px 18px -4px rgba(234, 88, 12, 0.12);
    }
    
    .card-asig {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        position: relative;
    }
    
    .badge-dias {
        background: #FEF3C7;
        color: #92400E;
        border: 1px solid #FDE68A;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 700;
        display: inline-block;
        margin-top: 6px;
    }
    
    .badge-urgente {
        background: #FEE2E2;
        color: #991B1B;
        border: 1px solid #FECACA;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 12px;
        font-weight: 700;
        display: inline-block;
        margin-top: 6px;
    }
    
    .apunte-container {
        background-color: white;
        border-left: 6px solid #EA580C;
        padding: 24px;
        border-radius: 14px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.04);
        line-height: 1.7;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #EA580C 0%, #C2410C 100%);
        color: white;
        border-radius: 10px;
        border: none;
        font-weight: 600;
        padding: 9px 20px;
    }
    .stButton>button:hover {
        opacity: 0.92;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# --- INICIALIZACIÓN CLIENTE GEMINI Y SERVIDOR GLOBAL ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)
except Exception:
    client = None

CARPETA_DATOS = Path("Campus_Familiar_Datos")
CARPETA_DATOS.mkdir(exist_ok=True)

# Executor a nivel de proceso del servidor (persistente ante cambios de página)
@st.cache_resource
def obtener_executor():
    return ThreadPoolExecutor(max_workers=3)

executor = obtener_executor()

# --- ESTADO DE SESIÓN ---
if "usuario_activo" not in st.session_state:
    st.session_state.usuario_activo = None
if "asig_actual" not in st.session_state:
    st.session_state.asig_actual = None
if "xp" not in st.session_state:
    st.session_state.xp = 210

# --- FUNCIONES DE ESTADO EN DISCO (PERSISTENCIA TOTAL) ---
def leer_estado_asig(ruta_asig):
    f_st = ruta_asig / "estado_sync.json"
    if f_st.exists():
        try:
            with open(f_st, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"estado": "idle", "progreso": "", "firma": ""}

def escribir_estado_asig(ruta_asig, data):
    f_st = ruta_asig / "estado_sync.json"
    with open(f_st, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def leer_meta_asig(ruta_asig):
    f_meta = ruta_asig / "metadata.json"
    if f_meta.exists():
        try:
            with open(f_meta, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"fecha_examen": None}

def escribir_meta_asig(ruta_asig, data):
    f_meta = ruta_asig / "metadata.json"
    with open(f_meta, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def cargar_config_usuario(ruta_usr):
    f_cfg = ruta_usr / "config.json"
    if f_cfg.exists():
        try:
            with open(f_cfg, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"nivel": "Universidad", "rama_bach": "Ciencias y Tecnología"}

def guardar_config_usuario(ruta_usr, data):
    f_cfg = ruta_usr / "config.json"
    with open(f_cfg, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- GENERADOR DE PDF (ReportLab) ---
def exportar_apuntes_pdf(titulo_asig, nivel, contenido_markdown):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm
    )
    styles = getSampleStyleSheet()
    
    t_style = ParagraphStyle('DocTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=20, leading=24, textColor=colors.HexColor('#EA580C'), spaceAfter=4)
    sub_style = ParagraphStyle('DocSub', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=colors.HexColor('#475569'), spaceAfter=14)
    h1_style = ParagraphStyle('H1', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=14, leading=18, textColor=colors.HexColor('#0F172A'), spaceBefore=12, spaceAfter=6)
    h2_style = ParagraphStyle('H2', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=15, textColor=colors.HexColor('#1E293B'), spaceBefore=8, spaceAfter=4)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontName='Helvetica', fontSize=9.5, leading=14, textColor=colors.HexColor('#334155'), spaceAfter=5)
    
    story = [
        Paragraph(f"Apuntes: {titulo_asig}", t_style),
        Paragraph(f"Nivel: {nivel} | Campus Inteligente de Estudio", sub_style),
        HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#EA580C'), spaceAfter=12)
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

# --- PROCESAMIENTO ASÍNCRONO PERSISTENTE ---
def tarea_fondo_procesar_archivos(api_key, ruta_asig_str, asig_nombre, nivel_edu, rama_bach, firma_nueva):
    ruta_asig = Path(ruta_asig_str)
    try:
        escribir_estado_asig(ruta_asig, {"estado": "running", "progreso": "Subiendo materiales a Gemini...", "firma": firma_nueva})
        cliente = genai.Client(api_key=api_key)
        
        archivos = [f for f in ruta_asig.glob("*") if f.is_file() and f.name not in ["apuntes_guardados.txt", "estado_sync.json", "metadata.json"]]
        archivos_remotos = []
        for r in archivos:
            if r.suffix.lower() in [".mp3", ".m4a", ".wav", ".pdf"]:
                sub = cliente.files.upload(file=str(r))
                archivos_remotos.append(sub)

        if "Bachillerato" in nivel_edu:
            contexto = f"ESTUDIANTE DE BACHILLERATO ({rama_bach}) - Castilla y León (BOCYL / LOMLOE). Adapta los conceptos y problemas a la rama de {rama_bach}."
        elif "Castilla y León" in nivel_edu:
            contexto = f"ESTUDIANTE ESCOLAR ({nivel_edu}) - Castilla y León (BOCYL / LOMLOE). Saberes básicos y didáctica escolar."
        else:
            contexto = "ESTUDIANTE UNIVERSITARIO (VIU). Máximo rigor historiográfico/académico. Foco estricto en los audios y PDFs subidos."

        prompt = f"""
        {contexto}
        Genera unos apuntes dinámicos, estructurados y completos para la asignatura: '{asig_nombre}'.
        Sintetiza minuciosamente los archivos de audio y documentos adjuntos.
        Usa títulos estructurados, tablas comparativas, resúmenes clave y esquemas en Markdown.
        """
        
        escribir_estado_asig(ruta_asig, {"estado": "running", "progreso": "Chopi está redactando los apuntes estructurados...", "firma": firma_nueva})
        
        res = cliente.models.generate_content(
            model='gemini-3.5-flash',
            contents=[prompt] + archivos_remotos
        )
        
        # Guardar apuntes en disco
        with open(ruta_asig / "apuntes_guardados.txt", "w", encoding="utf-8") as f:
            f.write(res.text)
            
        escribir_estado_asig(ruta_asig, {"estado": "done", "progreso": "Completado con éxito", "firma": firma_nueva})
    except Exception as e:
        escribir_estado_asig(ruta_asig, {"estado": "error", "progreso": f"Error: {str(e)}", "firma": firma_nueva})

def obtener_icono_asig(nombre):
    n = nombre.lower()
    if any(k in n for k in ["geo", "tierra", "mapa"]): return "🌍"
    if any(k in n for k in ["historia", "arte", "roma", "antigua", "medieval"]): return "🏛️"
    if any(k in n for k in ["lengua", "literatura", "idioma", "latin"]): return "📖"
    if any(k in n for k in ["mate", "algebra", "calculo", "fisica"]): return "📐"
    if any(k in n for k in ["bio", "ciencias", "naturales", "quimica", "salud"]): return "🧬"
    if any(k in n for k in ["filo", "etica", "pensamiento"]): return "💡"
    if any(k in n for k in ["ingles", "frances"]): return "🗣️"
    if any(k in n for k in ["musica", "audio"]): return "🎵"
    return "📚"

# --- CABECERA SUPERIOR ---
def render_chopi_header():
    nivel_chopi = (st.session_state.xp // 100) + 1
    col_c1, col_c2 = st.columns([5, 1])
    with col_c1:
        st.markdown(f"""
            <div class="chopi-header">
                <div class="chopi-avatar">🐕‍🦺</div>
                <div>
                    <h3 style="margin:0; color: #F8FAFC;">Chopi - Tu Compañero Patterdale Terrier</h3>
                    <p style="margin:3px 0 0 0; color: #94A3B8; font-size: 13.5px;">
                        Nivel <b>{nivel_chopi}</b> • XP: <b>{st.session_state.xp}</b> | Procesando clases en segundo plano continuo.
                    </p>
                </div>
            </div>
        """, unsafe_allow_html=True)
    with col_c2:
        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)
        if st.button("🍖 Premiar Chopi"):
            st.session_state.xp += 20
            st.balloons()
            st.rerun()

# ==============================================================================
# 1. PANTALLA PRINCIPAL (SELECCIÓN Y GESTIÓN DE USUARIOS)
# ==============================================================================
if st.session_state.usuario_activo is None:
    render_chopi_header()
    
    st.markdown("""
        <div class="hero-card">
            <h1 style="margin:0 0 8px 0; color: #0F172A; font-size: 28px;">🎓 Campus Educativo Inteligente</h1>
            <p style="margin:0; color: #475569; font-size: 15px;">
                Gestión simultánea para la Universidad (VIU) y las etapas escolares de Primaria, ESO y Bachillerato (Castilla y León).
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    tab_bienv, tab_tut, tab_admin = st.tabs(["🚀 Capacidades de la App", "📖 Tutorial Rápido", "⚙️ Añadir Estudiante"])
    
    with tab_bienv:
        c1, c2 = st.columns(2)
        c1.markdown("""
        #### 🎓 Universidad (VIU)
        * **Audios de clase de hasta 2 horas:** Súbelos y sigue navegando; se procesan en segundo plano sin cancelarse.
        * **Modo Estricto:** Fidelidad a tus apuntes sin invenciones externas.
        * **Cuenta atrás para exámenes:** Planificación temporal en días.
        """)
        c2.markdown("""
        #### 🎒 Colegio e Instituto (Castilla y León)
        * **Primaria y ESO:** Alineado con el currículo normativo (BOCYL).
        * **Bachillerato por Ramas:** Modalidades de Ciencias y Tecnología, Humanidades y Ciencias Sociales, o Salud.
        * **Exportación PDF:** Cuadernos limpios listos para imprimir.
        """)
        
    with tab_tut:
        st.markdown("""
        1. **Elige tu perfil** abajo.
        2. **Accede a tu Asignatura** y pon la **Fecha de Examen** para activar el contador de días.
        3. **Sube audios o PDFs:** Puedes salirte de la asignatura o cerrar la pestaña; Chopi seguirá trabajando en el servidor.
        4. Al terminar, descarga los **Apuntes en PDF** o genera un **Examen de Prueba**.
        """)
        
    with tab_admin:
        col_nu1, col_nu2, col_nu3 = st.columns([2, 2, 1])
        with col_nu1:
            nuevo_n = st.text_input("Nombre:")
        with col_nu2:
            nuevo_nv = st.selectbox("Etapa Académica:", [
                "Universidad", "Bachillerato (Castilla y León)", "ESO (Castilla y León)", "Primaria (Castilla y León)"
            ])
            rama = "General"
            if "Bachillerato" in nuevo_nv:
                rama = st.selectbox("Modalidad de Bachillerato:", [
                    "Ciencias y Tecnología", "Humanidades y Ciencias Sociales", "Ciencias de la Salud / Biosanitario"
                ])
        with col_nu3:
            st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
            if st.button("➕ Crear", use_container_width=True):
                if nuevo_n:
                    r = CARPETA_DATOS / nuevo_n
                    r.mkdir(exist_ok=True)
                    guardar_config_usuario(r, {"nivel": nuevo_nv, "rama_bach": rama})
                    st.success(f"Estudiante '{nuevo_n}' creado.")
                    st.rerun()

    st.markdown("---")
    st.subheader("👤 Selecciona tu Usuario:")
    
    perfiles = [d.name for d in CARPETA_DATOS.iterdir() if d.is_dir()]
    if perfiles:
        cols_usr = st.columns(max(len(perfiles), 3))
        for i, perf in enumerate(perfiles):
            r_perf = CARPETA_DATOS / perf
            cfg_p = cargar_config_usuario(r_perf)
            nv_p = cfg_p.get("nivel", "Universidad")
            rama_txt = f"({cfg_p.get('rama_bach', '')})" if "Bachillerato" in nv_p else ""
            with cols_usr[i % len(cols_usr)]:
                st.markdown(f"""
                    <div class="user-badge-card">
                        <div style="font-size: 38px; margin-bottom: 4px;">🧑‍🎓</div>
                        <h3 style="margin: 0; color: #0F172A;">{perf}</h3>
                        <p style="margin: 4px 0 10px 0; color: #64748B; font-size: 13px;">{nv_p} {rama_txt}</p>
                    </div>
                """, unsafe_allow_html=True)
                col_ub1, col_ub2 = st.columns([3, 1])
                if col_ub1.button(f"Entrar", key=f"sel_u_{perf}", use_container_width=True):
                    st.session_state.usuario_activo = perf
                    st.rerun()
                if col_ub2.button("🗑️", key=f"del_u_{perf}"):
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
    config_usr = cargar_config_usuario(ruta_usr)
    nivel_estudiante = config_usr.get("nivel", "Universidad")
    rama_bach = config_usr.get("rama_bach", "Ciencias y Tecnología")
    
    # Texto dinámico según etapa
    if "Primaria" in nivel_estudiante:
        texto_etapa = "🏫 Tus Asignaturas del Colegio"
    elif any(k in nivel_estudiante for k in ["ESO", "Bachillerato"]):
        texto_etapa = "🎒 Tus Asignaturas del Instituto"
    else:
        texto_etapa = "🎓 Tus Asignaturas de la Universidad (VIU)"

    with st.sidebar:
        st.markdown(f"### 👤 {usr_actual}")
        st.caption(f"**{nivel_estudiante}**")
        if "Bachillerato" in nivel_estudiante:
            st.caption(f"Rama: *{rama_bach}*")
            
        if st.button("🚪 Cambiar de Usuario", use_container_width=True):
            st.session_state.usuario_activo = None
            st.session_state.asig_actual = None
            st.rerun()

    # --------------------------------------------------------------------------
    # 2.1 LISTADO DE ASIGNATURAS
    # --------------------------------------------------------------------------
    if st.session_state.asig_actual is None:
        st.markdown(f"""
            <div class="hero-card">
                <h2 style="margin: 0 0 4px 0; color: #0F172A;">{texto_etapa}</h2>
                <p style="margin:0; color: #64748B;">Perfil de estudio: <b>{usr_actual}</b> {f'— Rama: {rama_bach}' if "Bachillerato" in nivel_estudiante else ''}</p>
            </div>
        """, unsafe_allow_html=True)
        
        col_a1, col_a2 = st.columns([3, 1])
        with col_a1:
            nom_asig = st.text_input("Nueva Asignatura:", placeholder="Ej. Historia Medieval, Biología y Geología, Filosofía...", label_visibility="collapsed")
        with col_a2:
            if st.button("➕ Añadir Asignatura", use_container_width=True):
                if nom_asig:
                    (ruta_usr / nom_asig).mkdir(exist_ok=True)
                    st.rerun()
                    
        asigs = [d.name for d in ruta_usr.iterdir() if d.is_dir()]
        if not asigs:
            st.info("No hay asignaturas creadas todavía. Añade una arriba.")
        else:
            cols_as = st.columns(3)
            for idx, a_name in enumerate(asigs):
                r_as = ruta_usr / a_name
                ic = obtener_icono_asig(a_name)
                meta = leer_meta_asig(r_as)
                estado_sync = leer_estado_asig(r_as)
                
                # Cálculo de días para el examen
                badge_examen = ""
                if meta.get("fecha_examen"):
                    f_ex = datetime.strptime(meta["fecha_examen"], "%Y-%m-%d").date()
                    delta = (f_ex - date.today()).days
                    if delta > 0:
                        badge_examen = f'<div class="badge-dias">⏳ Examen en {delta} días</div>'
                    elif delta == 0:
                        badge_examen = '<div class="badge-urgente">🔥 ¡El examen es HOY!</div>'
                    else:
                        badge_examen = '<div class="badge-dias">✅ Examen pasado</div>'
                
                aviso_sync = ""
                if estado_sync.get("estado") == "running":
                    aviso_sync = "<div style='color: #EA580C; font-size: 11px; font-weight: bold; margin-top: 4px;'>⚙️ Procesando en fondo...</div>"
                
                with cols_as[idx % 3]:
                    st.markdown(f"""
                        <div class="card-asig">
                            <div style="font-size: 38px; margin-bottom: 6px;">{ic}</div>
                            <h4 style="margin: 0; color: #0F172A;">{a_name}</h4>
                            {badge_examen}
                            {aviso_sync}
                        </div>
                    """, unsafe_allow_html=True)
                    col_b1, col_b2 = st.columns([3, 1])
                    if col_b1.button("📂 Entrar", key=f"entrar_{a_name}", use_container_width=True):
                        st.session_state.asig_actual = a_name
                        st.rerun()
                    if col_b2.button("🗑️", key=f"del_a_{a_name}"):
                        import shutil
                        shutil.rmtree(r_as)
                        st.rerun()

    # --------------------------------------------------------------------------
    # 2.2 DENTRO DE LA ASIGNATURA
    # --------------------------------------------------------------------------
    else:
        asig_sel = st.session_state.asig_actual
        ruta_asig = ruta_usr / asig_sel
        icono_materia = obtener_icono_asig(asig_sel)
        meta_asig = leer_meta_asig(ruta_asig)
        estado_asig = leer_estado_asig(ruta_asig)
        
        col_nv1, col_nv2 = st.columns([1, 3])
        with col_nv1:
            if st.button("⬅️ Volver a Asignaturas"):
                st.session_state.asig_actual = None
                st.rerun()
                
        # Barra de Examen y Cuenta Atrás
        with col_nv2:
            f_actual = None
            if meta_asig.get("fecha_examen"):
                f_actual = datetime.strptime(meta_asig["fecha_examen"], "%Y-%m-%d").date()
            
            with st.popover("📅 Configurar Fecha de Examen"):
                nueva_f = st.date_input("Fecha del próximo examen:", value=f_actual if f_actual else date.today())
                if st.button("Guardar Fecha"):
                    meta_asig["fecha_examen"] = str(nueva_f)
                    escribir_meta_asig(ruta_asig, meta_asig)
                    st.rerun()

        st.markdown(f"## {icono_materia} {asig_sel}")
        
        if meta_asig.get("fecha_examen"):
            f_ex = datetime.strptime(meta_asig["fecha_examen"], "%Y-%m-%d").date()
            delta = (f_ex - date.today()).days
            if delta >= 0:
                st.info(f"⏳ **Cuenta atrás:** Faltan **{delta} días** para el examen ({f_ex.strftime('%d/%m/%Y')}). ¡A por ello!")
            else:
                st.caption(f"Examen realizado el {f_ex.strftime('%d/%m/%Y')}.")

        tab_mat, tab_ap, tab_ex, tab_tut = st.tabs([
            "📂 Materiales & Auto-Sync", 
            "✨ Apuntes Dinámicos (PDF)", 
            "🎯 Batería de Exámenes", 
            "🤖 Tutor Particular"
        ])
        
        # --- TAB 1: ARCHIVOS Y LANZAMIENTO GLOBAL ---
        with tab_mat:
            st.subheader("Subida de Materiales y Grabaciones de Clase")
            st.caption("Los audios y PDFs se procesan en segundo plano en el servidor. Puedes salirte sin que se cancele.")
            
            subidos = st.file_uploader(
                "Sube archivos (PDF, MP3, M4A de hasta 2 horas):",
                type=["pdf", "mp3", "m4a", "wav"],
                accept_multiple_files=True
            )
            
            if subidos:
                for arc in subidos:
                    with open(ruta_asig / arc.name, "wb") as f:
                        f.write(arc.getbuffer())
                st.success("Archivos guardados correctamente.")
                st.rerun()
                
            archivos_actuales = [f for f in ruta_asig.glob("*") if f.is_file() and f.name not in ["apuntes_guardados.txt", "estado_sync.json", "metadata.json"]]
            
            # Comprobar firma para disparo en fondo
            firma_actual = f"{len(archivos_actuales)}_" + "_".join(sorted([f"{f.name}_{f.stat().st_size}" for f in archivos_actuales]))
            firma_guardada = estado_asig.get("firma", "")
            
            if firma_actual != firma_guardada and archivos_actuales and estado_asig.get("estado") != "running" and client:
                # Lanzar en el Executor global (no se detiene si sales)
                executor.submit(
                    tarea_fondo_procesar_archivos,
                    API_KEY, str(ruta_asig), asig_sel, nivel_estudiante, rama_bach, firma_actual
                )
                st.info("🔄 Se han detectado nuevos archivos. Procesamiento lanzado en segundo plano.")
                st.rerun()
                
            st.markdown("---")
            st.markdown("#### 📄 Archivos Guardados:")
            if archivos_actuales:
                for f in archivos_actuales:
                    cf1, cf2 = st.columns([4, 1])
                    tam = round(f.stat().st_size / (1024 * 1024), 2)
                    cf1.text(f"• {f.name} ({tam} MB)")
                    if cf2.button("🗑️", key=f"delf_{f.name}"):
                        f.unlink()
                        st.rerun()
            else:
                st.info("No hay archivos subidos.")

        # --- TAB 2: APUNTES ---
        with tab_ap:
            st.subheader("✨ Cuaderno de Apuntes Dinámicos")
            estado_actual = leer_estado_asig(ruta_asig)
            
            if estado_actual.get("estado") == "running":
                st.warning(f"⏳ **Chopi está trabajando:** {estado_actual.get('progreso')} (Puedes salirte tranquilamente).")
                if st.button("🔄 Comprobar si ha terminado"):
                    st.rerun()
                    
            f_apuntes = ruta_asig / "apuntes_guardados.txt"
            if f_apuntes.exists():
                with open(f_apuntes, "r", encoding="utf-8") as f:
                    txt_ap = f.read()
                    
                col_d1, col_d2 = st.columns([3, 1])
                with col_d2:
                    pdf_bytes = exportar_apuntes_pdf(asig_sel, f"{nivel_estudiante} ({rama_bach})" if "Bachillerato" in nivel_estudiante else nivel_estudiante, txt_ap)
                    st.download_button(
                        label="📄 Descargar en PDF",
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
                if estado_actual.get("estado") != "running":
                    st.info("Sube archivos en la pestaña 'Materiales' o pulsa abajo para generar apuntes curriculares oficiales.")
                    if st.button("🚀 Generar desde Currículo Oficial"):
                        if client:
                            executor.submit(
                                tarea_fondo_procesar_archivos,
                                API_KEY, str(ruta_asig), asig_sel, nivel_estudiante, rama_bach, "manual"
                            )
                            st.rerun()

        # --- TAB 3: EXÁMENES ---
        with tab_ex:
            st.subheader("🎯 Batería de Exámenes")
            tipo_e = st.selectbox("Modalidad:", ["Test con soluciones razonadas", "Preguntas de Desarrollo", "Mixto"])
            num_p = st.slider("Número de preguntas:", 5, 30, 10)
            
            if st.button("🚀 Generar Examen"):
                if client:
                    with st.spinner("Redactando examen adaptado..."):
                        p_ex = f"""
                        Genera un examen de {tipo_e} ({num_p} preguntas) para {asig_sel}.
                        Nivel: {nivel_estudiante} {f'- Modalidad: {rama_bach}' if 'Bachillerato' in nivel_estudiante else ''}.
                        Si es universitario, exige análisis historiográfico. Si es Bachillerato/ESO/Primaria, sigue la normativa de Castilla y León.
                        Incluye respuestas y criterios de corrección al final.
                        """
                        res_ex = client.models.generate_content(model='gemini-3.5-flash', contents=p_ex)
                        st.session_state[f"ex_{asig_sel}"] = res_ex.text
                        st.session_state.xp += 30
                        st.rerun()
                        
            if f"ex_{asig_sel}" in st.session_state:
                st.markdown("---")
                st.markdown(st.session_state[f"ex_{asig_sel}"])

        # --- TAB 4: TUTOR ---
        with tab_tut:
            st.subheader("🤖 Tutor Particular")
            duda = st.text_input("Formula tu pregunta académica:")
            if duda and client:
                with st.spinner("Pensando respuesta..."):
                    res_tut = client.models.generate_content(
                        model='gemini-3.5-flash',
                        contents=f"Responde como docente de {asig_sel} para {nivel_estudiante} ({rama_bach}): {duda}"
                    )
                    st.markdown(res_tut.text)
