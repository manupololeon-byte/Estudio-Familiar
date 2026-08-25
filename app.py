import streamlit as st
import os
import json
import io
import hashlib
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

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    .main { background-color: #F8FAFC; }
    
    @keyframes petFloat {
        0%, 100% { transform: translateY(0px); }
        50% { transform: translateY(-5px); }
    }
    
    .chopi-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        border: 1px solid #334155;
        border-radius: 18px;
        padding: 18px 24px;
        color: white;
        display: flex;
        align-items: center;
        gap: 16px;
        box-shadow: 0 8px 20px rgba(15, 23, 42, 0.12);
        margin-bottom: 20px;
    }
    
    .chopi-avatar {
        font-size: 44px;
        background: #1E293B;
        border: 2px solid #F59E0B;
        border-radius: 50%;
        padding: 6px 10px;
        animation: petFloat 3.5s ease-in-out infinite;
    }
    
    .hero-card {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 16px;
        padding: 22px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.03);
    }
    
    .card-asig {
        background: white;
        border: 1px solid #E2E8F0;
        border-radius: 14px;
        padding: 18px;
        text-align: center;
    }
    
    .badge-dias {
        background: #FEF3C7; color: #92400E; border: 1px solid #FDE68A;
        padding: 3px 8px; border-radius: 10px; font-size: 11px; font-weight: 700;
        display: inline-block; margin-top: 4px;
    }
    
    .apunte-container {
        background-color: white;
        border-left: 5px solid #EA580C;
        padding: 22px;
        border-radius: 12px;
        box-shadow: 0 3px 8px rgba(0,0,0,0.03);
        line-height: 1.65;
    }
    
    .stButton>button {
        background: linear-gradient(135deg, #EA580C 0%, #C2410C 100%);
        color: white; border-radius: 8px; border: none; font-weight: 600; padding: 8px 18px;
    }
    </style>
""", unsafe_allow_html=True)

# --- CLIENTE Y EXECUTOR ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)
except Exception:
    client = None

CARPETA_DATOS = Path("Campus_Familiar_Datos")
CARPETA_DATOS.mkdir(exist_ok=True)

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
    st.session_state.xp = 220

# --- FUNCIONES DE PERSISTENCIA Y METADATOS ---
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

def calcular_hash_archivos(ruta_asig):
    archivos = sorted([f for f in ruta_asig.glob("*") if f.is_file() and f.name not in ["apuntes_guardados.txt", "estado_sync.json", "metadata.json", "examenes_historial.json"]])
    cadena = "|".join([f"{f.name}:{f.stat().st_size}:{f.stat().st_mtime}" for f in archivos])
    return hashlib.md5(cadena.encode("utf-8")).hexdigest(), archivos

# --- GENERADOR DE PDF (ReportLab) ---
def exportar_apuntes_pdf(titulo_asig, nivel, contenido_markdown):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    
    t_style = ParagraphStyle('DocTitle', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=18, leading=22, textColor=colors.HexColor('#EA580C'), spaceAfter=4)
    sub_style = ParagraphStyle('DocSub', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=10, leading=13, textColor=colors.HexColor('#475569'), spaceAfter=12)
    h1_style = ParagraphStyle('H1', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=13, leading=17, textColor=colors.HexColor('#0F172A'), spaceBefore=10, spaceAfter=4)
    h2_style = ParagraphStyle('H2', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=11, leading=14, textColor=colors.HexColor('#1E293B'), spaceBefore=7, spaceAfter=3)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontName='Helvetica', fontSize=9, leading=13, textColor=colors.HexColor('#334155'), spaceAfter=4)
    
    story = [
        Paragraph(f"Apuntes: {titulo_asig}", t_style),
        Paragraph(f"Nivel: {nivel} | Campus Inteligente", sub_style),
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

# --- TRABAJADOR EN SEGUNDO PLANO PARA APUNTES AUTOMÁTICOS ---
def tarea_fondo_apuntes_auto(api_key, ruta_asig_str, asig_nombre, nivel_edu, rama_bach, firma_hash):
    ruta_asig = Path(ruta_asig_str)
    f_estado = ruta_asig / "estado_sync.json"
    try:
        escribir_json(f_estado, {"estado": "running", "progreso": "Subiendo materiales a Gemini...", "firma": firma_hash})
        cliente = genai.Client(api_key=api_key)
        
        archivos = [f for f in ruta_asig.glob("*") if f.is_file() and f.name not in ["apuntes_guardados.txt", "estado_sync.json", "metadata.json", "examenes_historial.json"]]
        archivos_remotos = []
        for r in archivos:
            if r.suffix.lower() in [".mp3", ".m4a", ".wav", ".pdf"]:
                sub = cliente.files.upload(file=str(r))
                archivos_remotos.append(sub)

        if "Bachillerato" in nivel_edu:
            ctx = f"ESTUDIANTE DE BACHILLERATO ({rama_bach}) - Castilla y León (BOCYL / LOMLOE)."
        elif "Castilla y León" in nivel_edu:
            ctx = f"ESTUDIANTE ESCOLAR ({nivel_edu}) - Castilla y León (BOCYL / LOMLOE)."
        else:
            ctx = "ESTUDIANTE UNIVERSITARIO (VIU - Historia). Máximo rigor formal e historiográfico. Sintetiza minuciosamente los audios y PDFs adjuntos."

        prompt = f"""
        {ctx}
        Genera unos apuntes dinámicos, estructurados y completos para la asignatura: '{asig_nombre}'.
        Sintetiza minuciosamente los archivos de audio y documentos adjuntos.
        Usa títulos estructurados, tablas comparativas, resúmenes clave y esquemas en Markdown.
        """
        
        escribir_json(f_estado, {"estado": "running", "progreso": "Redactando los apuntes estructurados...", "firma": firma_hash})
        
        res = cliente.models.generate_content(
            model='gemini-3.5-flash',
            contents=[prompt] + archivos_remotos
        )
        
        with open(ruta_asig / "apuntes_guardados.txt", "w", encoding="utf-8") as f:
            f.write(res.text)
            
        escribir_json(f_estado, {"estado": "done", "progreso": "Completado", "firma": firma_hash})
    except Exception as e:
        escribir_json(f_estado, {"estado": "error", "progreso": f"Error: {str(e)}", "firma": firma_hash})

def disparar_sync_si_es_necesario(ruta_asig, asig_nombre, nivel_edu, rama_bach):
    f_estado = ruta_asig / "estado_sync.json"
    estado_dict = leer_json(f_estado, {"estado": "idle", "firma": ""})
    hash_actual, archivos = calcular_hash_archivos(ruta_asig)
    
    if hash_actual != estado_dict.get("firma") and archivos and estado_dict.get("estado") != "running" and client:
        executor.submit(
            tarea_fondo_apuntes_auto,
            API_KEY, str(ruta_asig), asig_nombre, nivel_edu, rama_bach, hash_actual
        )
        escribir_json(f_estado, {"estado": "running", "progreso": "Iniciando sincronización automática...", "firma": hash_actual})

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
                    <h3 style="margin:0; color: #F8FAFC;">Chopi - Patterdale Terrier</h3>
                    <p style="margin:2px 0 0 0; color: #94A3B8; font-size: 13px;">
                        Nivel <b>{nivel_chopi}</b> • XP: <b>{st.session_state.xp}</b> | Procesamiento persistente y exámenes activos.
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
# 1. PANTALLA PRINCIPAL GLOBAL
# ==============================================================================
if st.session_state.usuario_activo is None:
    render_chopi_header()
    
    st.markdown("""
        <div class="hero-card">
            <h1 style="margin:0 0 6px 0; color: #0F172A; font-size: 26px;">🎓 Campus Educativo Inteligente</h1>
            <p style="margin:0; color: #475569; font-size: 14.5px;">
                Gestión de estudios universitarios (VIU) y escolares (Castilla y León).
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    tab_bienv, tab_tut, tab_admin = st.tabs(["🚀 Capacidades", "📖 Tutorial", "⚙️ Gestión de Usuarios"])
    
    with tab_bienv:
        c1, c2 = st.columns(2)
        c1.markdown("""
        #### 🎓 Universidad (VIU)
        * **Audios de clase de hasta 2 horas:** Súbelos y sigue navegando; se procesan en segundo plano.
        * **Exámenes Interactivos:** Con selección de materiales y corrección razonada.
        * **Corrector de Trabajos:** Evaluación con rúbrica o criterios universitarios de Grado de Historia (0 a 10).
        """)
        c2.markdown("""
        #### 🎒 Colegio e Instituto (Castilla y León)
        * **Primaria, ESO y Bachillerato:** Ajustado a los saberes y criterios oficiales de CyL.
        * **Modalidades de Bachillerato:** Ciencias, Humanidades o Salud.
        * **Auto-Sync y PDF:** Los apuntes se actualizan solos al subir archivos y se descargan en PDF limpio.
        """)
        
    with tab_tut:
        st.markdown("""
        1. **Selecciona tu Perfil** abajo.
        2. **Entra en tu Asignatura** y sube PDFs o audios: los apuntes se actualizarán solos.
        3. Ve a **🎯 Exámenes Interactivos** para responder preguntas tipo test y obtener tu nota media acumulada.
        4. Ve a **📑 Corrector de Trabajos** para evaluar ensayos con nota ponderada.
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
    st.subheader("👤 Elige Estudiante:")
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
                    <div class="card-asig">
                        <div style="font-size: 34px;">🧑‍🎓</div>
                        <h4 style="margin: 4px 0; color: #0F172A;">{perf}</h4>
                        <p style="margin:0 0 10px 0; color: #64748B; font-size: 12px;">{nv_p} {rama_txt}</p>
                    </div>
                """, unsafe_allow_html=True)
                col_b1, col_b2 = st.columns([3, 1])
                if col_b1.button("Entrar", key=f"sel_u_{perf}", use_container_width=True):
                    st.session_state.usuario_activo = perf
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
                <p style="margin:0; color: #64748B;">Estudiante activo: <b>{usr_actual}</b></p>
            </div>
        """, unsafe_allow_html=True)
        
        col_a1, col_a2 = st.columns([3, 1])
        with col_a1:
            nom_asig = st.text_input("Nueva Asignatura:", placeholder="Ej. Historia Medieval, Lengua Castellana...", label_visibility="collapsed")
        with col_a2:
            if st.button("➕ Añadir Asignatura", use_container_width=True):
                if nom_asig:
                    (ruta_usr / nom_asig).mkdir(exist_ok=True)
                    st.rerun()
                    
        asigs = [d.name for d in ruta_usr.iterdir() if d.is_dir()]
        if not asigs:
            st.info("No hay asignaturas creadas en este perfil.")
        else:
            cols_as = st.columns(3)
            for idx, a_name in enumerate(asigs):
                r_as = ruta_usr / a_name
                ic = obtener_icono_asig(a_name)
                meta = leer_json(r_as / "metadata.json", {})
                estado_sync = leer_json(r_as / "estado_sync.json", {})
                historial_ex = leer_json(r_as / "examenes_historial.json", [])
                
                # Nota media
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
                
                aviso_sync = ""
                if estado_sync.get("estado") == "running":
                    aviso_sync = "<div style='color: #EA580C; font-size: 11px; font-weight: bold;'>⚙️ Procesando apuntes...</div>"
                
                with cols_as[idx % 3]:
                    st.markdown(f"""
                        <div class="card-asig">
                            <div style="font-size: 34px;">{ic}</div>
                            <h4 style="margin: 2px 0 6px 0; color: #0F172A;">{a_name}</h4>
                            {badge_examen}
                            {nota_media_txt}
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
        meta_asig = leer_json(ruta_asig / "metadata.json", {})
        
        # Disparar sincronización automática si cambiaron los archivos
        disparar_sync_si_es_necesario(ruta_asig, asig_sel, nivel_estudiante, rama_bach)
        
        col_nv1, col_nv2 = st.columns([1, 3])
        with col_nv1:
            if st.button("⬅️ Volver al listado"):
                st.session_state.asig_actual = None
                st.rerun()
                
        with col_nv2:
            f_actual = None
            if meta_asig.get("fecha_examen"):
                f_actual = datetime.strptime(meta_asig["fecha_examen"], "%Y-%m-%d").date()
            with st.popover("📅 Configurar Fecha de Examen"):
                nueva_f = st.date_input("Fecha de examen:", value=f_actual if f_actual else date.today())
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

        tab_mat, tab_ap, tab_ex, tab_trabajos, tab_tut = st.tabs([
            "📂 Materiales & Auto-Sync", 
            "✨ Apuntes Dinámicos (PDF)", 
            "🎯 Exámenes Interactivos", 
            "📑 Corrector de Trabajos",
            "🤖 Tutor Particular"
        ])
        
        # --- TAB 1: MATERIALES ---
        with tab_mat:
            st.subheader("Subida de Materiales (PDFs y Audios de hasta 2 horas)")
            st.caption("Al terminar de subir o borrar archivos, los apuntes dinámicos se regenerarán solos automáticamente en segundo plano.")
            
            subidos = st.file_uploader(
                "Sube materiales:",
                type=["pdf", "mp3", "m4a", "wav"],
                accept_multiple_files=True
            )
            
            if subidos:
                for arc in subidos:
                    with open(ruta_asig / arc.name, "wb") as f:
                        f.write(arc.getbuffer())
                st.success("Archivos guardados. Sincronización automática iniciada.")
                st.rerun()
                
            archivos_actuales = [f for f in ruta_asig.glob("*") if f.is_file() and f.name not in ["apuntes_guardados.txt", "estado_sync.json", "metadata.json", "examenes_historial.json"]]
            
            if archivos_actuales:
                st.markdown("#### 📄 Archivos Guardados:")
                for f in archivos_actuales:
                    cf1, cf2 = st.columns([4, 1])
                    tam = round(f.stat().st_size / (1024 * 1024), 2)
                    cf1.text(f"• {f.name} ({tam} MB)")
                    if cf2.button("🗑️", key=f"delf_{f.name}"):
                        f.unlink()
                        st.rerun()
            else:
                st.info("No hay archivos subidos todavía.")

        # --- TAB 2: APUNTES ---
        with tab_ap:
            st.subheader("✨ Apuntes Dinámicos")
            estado_actual = leer_json(ruta_asig / "estado_sync.json", {})
            
            if estado_actual.get("estado") == "running":
                st.warning(f"⏳ **Chopi está procesando los apuntes:** {estado_actual.get('progreso')} (Puedes hacer exámenes mientras tanto).")
                if st.button("🔄 Actualizar estado"):
                    st.rerun()
                    
            f_apuntes = ruta_asig / "apuntes_guardados.txt"
            if f_apuntes.exists():
                with open(f_apuntes, "r", encoding="utf-8") as f:
                    txt_ap = f.read()
                    
                col_d1, col_d2 = st.columns([3, 1])
                with col_d2:
                    pdf_bytes = exportar_apuntes_pdf(asig_sel, f"{nivel_estudiante} ({rama_bach})" if "Bachillerato" in nivel_estudiante else nivel_estudiante, txt_ap)
                    st.download_button(
                        label="📄 Descargar en PDF Maquetado",
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
                st.info("Sube archivos en la pestaña 'Materiales' para que los apuntes se creen automáticamente.")

        # --- TAB 3: EXÁMENES INTERACTIVOS CON NOTA MEDIA Y EXPLICACIÓN ---
        with tab_ex:
            st.subheader("🎯 Exámenes Interactivos con Corrección y Nota Media")
            
            historial_ex = leer_json(ruta_asig / "examenes_historial.json", [])
            if historial_ex:
                media_total = sum([x["nota"] for x in historial_ex]) / len(historial_ex)
                st.success(f"📊 **Nota Media Acumulada en {asig_sel}: {media_total:.2f} / 10** (sobre {len(historial_ex)} exámenes realizados)")
            
            st.markdown("---")
            st.markdown("#### 1. Selección de Materiales para el Examen:")
            archivos_disponibles = [f.name for f in ruta_asig.glob("*") if f.is_file() and f.name not in ["apuntes_guardados.txt", "estado_sync.json", "metadata.json", "examenes_historial.json"]]
            
            elegir_todos = st.checkbox("✅ Seleccionar todos los materiales disponibles", value=True)
            materiales_seleccionados = []
            
            if not elegir_todos and archivos_disponibles:
                st.caption("Marca los temas o archivos específicos:")
                for arc_n in archivos_disponibles:
                    if st.checkbox(arc_n, value=False, key=f"mat_sel_{arc_n}"):
                        materiales_seleccionados.append(arc_n)
            else:
                materiales_seleccionados = archivos_disponibles
                
            num_p = st.slider("Número de preguntas tipo test:", min_value=3, max_value=20, value=5)
            
            if st.button("🚀 Comenzar Nuevo Examen Interactivo"):
                if client:
                    with st.spinner("Chopi está redactando las preguntas interactivas..."):
                        prompt_json = f"""
                        Genera un examen interactivo de tipo test ({num_p} preguntas) para la asignatura: {asig_sel}.
                        Nivel: {nivel_estudiante} {f'({rama_bach})' if 'Bachillerato' in nivel_estudiante else ''}.
                        Materiales seleccionados: {', '.join(materiales_seleccionados) if materiales_seleccionados else 'Currículo oficial'}.
                        
                        Devuelve EXCLUSIVAMENTE un array JSON válido con este formato:
                        [
                          {{
                            "pregunta": "¿Texto de la pregunta?",
                            "opciones": ["Opción A", "Opción B", "Opción C", "Opción D"],
                            "correcta": 0,
                            "explicacion": "Explicación detallada de por qué esta es la respuesta correcta y qué falló en las demás."
                          }}
                        ]
                        """
                        try:
                            res = client.models.generate_content(
                                model='gemini-3.5-flash',
                                contents=prompt_json
                            )
                            raw_text = res.text.strip()
                            if raw_text.startswith("```json"):
                                raw_text = raw_text[7:]
                            if raw_text.endswith("```"):
                                raw_text = raw_text[:-3]
                            st.session_state[f"examen_activo_{asig_sel}"] = json.loads(raw_text.strip())
                            st.session_state[f"respuestas_usuario_{asig_sel}"] = {}
                            st.session_state[f"corregido_{asig_sel}"] = False
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al generar examen: {e}")

            # RENDERIZADO DEL EXAMEN INTERACTIVO
            if f"examen_activo_{asig_sel}" in st.session_state:
                preguntas_examen = st.session_state[f"examen_activo_{asig_sel}"]
                st.markdown("### 📝 Cuestionario Activo")
                
                for i, p in enumerate(preguntas_examen):
                    st.markdown(f"**Pregunta {i+1}: {p['pregunta']}**")
                    st.session_state[f"respuestas_usuario_{asig_sel}"][i] = st.radio(
                        f"Selecciona tu respuesta para la pregunta {i+1}:",
                        options=list(range(len(p["opciones"]))),
                        format_func=lambda opt_idx: p["opciones"][opt_idx],
                        key=f"radio_p_{asig_sel}_{i}",
                        label_visibility="collapsed"
                    )
                    st.markdown("---")
                    
                if st.button("🏁 Terminar y Corregir Examen"):
                    st.session_state[f"corregido_{asig_sel}"] = True
                    
                if st.session_state.get(f"corregido_{asig_sel}", False):
                    aciertos = 0
                    st.markdown("## 📊 Resultados y Corrección Explicada")
                    
                    for i, p in enumerate(preguntas_examen):
                        resp_user = st.session_state[f"respuestas_usuario_{asig_sel}"].get(i, None)
                        es_correcta = (resp_user == p["correcta"])
                        if es_correcta:
                            aciertos += 1
                            st.success(f"✅ **Pregunta {i+1}: ¡Correcta!**\n\nTu respuesta: {p['opciones'][resp_user]}\n\n💡 *{p['explicacion']}*")
                        else:
                            st.error(f"❌ **Pregunta {i+1}: Incorrecta**\n\nTu respuesta: {p['opciones'][resp_user] if resp_user is not None else 'Sin responder'}\n\nRespuesta correcta: **{p['opciones'][p['correcta']]}**\n\n💡 **¿Por qué has fallado?:** {p['explicacion']}")
                            
                    nota_obtenida = round((aciertos / len(preguntas_examen)) * 10, 2)
                    st.markdown(f"### 🏆 Calificación Final: **{nota_obtenida} / 10**")
                    
                    if st.button("💾 Guardar Nota en mi Expediente"):
                        historial_ex.append({
                            "fecha": str(date.today()),
                            "nota": nota_obtenida,
                            "preguntas": len(preguntas_examen)
                        })
                        escribir_json(ruta_asig / "examenes_historial.json", historial_ex)
                        st.session_state.xp += int(nota_obtenida * 5)
                        st.success("¡Nota registrada! Se ha recalculado tu nota media.")
                        del st.session_state[f"examen_activo_{asig_sel}"]
                        st.rerun()

        # --- TAB 4: AUDITOR / CORRECTOR DE TRABAJOS CON RÚBRICA ---
        with tab_trabajos:
            st.subheader("📑 Corrector y Evaluador de Trabajos y Ensayos")
            st.caption("Evalúa tu trabajo con una rúbrica propia o mediante los criterios formales de Grado de Historia universitario.")
            
            trabajo_texto = st.text_area("Pega aquí el texto completo de tu trabajo o ensayo:", height=220)
            rubrica_usuario = st.text_area("Rúbrica o criterios de evaluación específicos (opcional):", placeholder="Si lo dejas en blanco, aplicará los criterios de evaluación de Grado de Historia universitario (aparato crítico, rigor metodológico, historiografía y ortotipografía)...", height=90)
            
            if st.button("🔍 Evaluar y Corregir Trabajo"):
                if trabajo_texto and client:
                    with st.spinner("Evaluando trabajo con rigor académico..."):
                        if rubrica_usuario.strip():
                            instruccion_correccion = f"Aplica estrictamente esta rúbrica proporcionada por el estudiante: {rubrica_usuario}"
                        else:
                            instruccion_correccion = """
                            Aplica los criterios de evaluación de un Grado Universitario en Historia:
                            1. Rigor conceptual y manejo del vocabulario historiográfico.
                            2. Estructura argumentativa, coherencia lógica y profundidad de análisis.
                            3. Aparato crítico, contextualización cronológica y fuentes.
                            4. Corrección ortográfica, sintáctica y adecuación formal.
                            """
                            
                        prompt_eval = f"""
                        Actúa como un profesor universitario titular del Grado de Historia.
                        Evalúa el siguiente trabajo presentado para la asignatura: {asig_sel}.
                        
                        {instruccion_correccion}
                        
                        Trabajo del alumno:
                        \"\"\"{trabajo_texto}\"\"\"
                        
                        Estructura tu respuesta exactamente así:
                        1. **Calificación Final Ponderada (0 a 10):** (Indica la nota con un decimal bien justificado).
                        2. **Puntos Fuertes:** (Aspectos destacados del trabajo).
                        3. **Errores Detectados y Puntos de Mejora:** (Detalla fallos historiográficos, conceptuales o formales).
                        4. **Sugerencias de Redacción y Ampliación:** (Propuestas concretas para subir la nota).
                        """
                        res_eval = client.models.generate_content(
                            model='gemini-3.5-flash',
                            contents=prompt_eval
                        )
                        st.session_state[f"evaluacion_{asig_sel}"] = res_eval.text
                        st.session_state.xp += 40
                        st.rerun()

            if f"evaluacion_{asig_sel}" in st.session_state:
                st.markdown("---")
                st.markdown(st.session_state[f"evaluacion_{asig_sel}"])

        # --- TAB 5: TUTOR ---
        with tab_tut:
            st.subheader("🤖 Tutor Particular")
            duda = st.text_input("Formula tu consulta académica:")
            if duda and client:
                with st.spinner("Pensando respuesta..."):
                    res_tut = client.models.generate_content(
                        model='gemini-3.5-flash',
                        contents=f"Responde como docente especializado en {asig_sel} para nivel {nivel_estudiante} ({rama_bach}): {duda}"
                    )
                    st.markdown(res_tut.text)
