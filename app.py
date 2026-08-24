import streamlit as st
import streamlit.components.v1 as components
from google import genai
import PyPDF2
import os
import shutil
import json
import re
import time
from datetime import datetime, date
from io import BytesIO

# --- FUNCIÓN PARA CREAR PDFs GRÁFICOS Y DE DISEÑO AVANZADO ---
try:
    from fpdf import FPDF
except ImportError:
    st.error("Falta instalar la librería de PDFs. Escribe en el terminal: python3 -m pip install fpdf")

# --- FUNCIÓN PARA PODCASTS ---
try:
    from gtts import gTTS
except ImportError:
    st.error("Falta instalar la librería de audio. Escribe en el terminal: python3 -m pip install gTTS")

class PDFGrafico(FPDF):
    def __init__(self, titulo_asignatura="", nivel=""):
        super().__init__()
        self.titulo_asignatura = titulo_asignatura
        self.nivel = nivel

    def header(self):
        self.set_fill_color(227, 82, 5) # Naranja corporativo
        self.rect(0, 0, 210, 15, 'F')
        self.set_font('Arial', 'B', 9)
        self.set_text_color(255, 255, 255)
        self.cell(0, 8, f"CAMPUS EDUCATIVO | NIVEL: {self.nivel.upper()} | {self.titulo_asignatura.upper()}", 0, 1, 'R')
        self.ln(12)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(100, 100, 100)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def limpiar_emojis_para_pdf(texto):
    return re.sub(r'[^\x00-\x7F\u00C0-\u00FF]+', '', texto)

def generar_pdf_grafico_ilustrado(texto_markdown, asignatura, nivel):
    pdf = PDFGrafico(titulo_asignatura=asignatura, nivel=nivel)
    pdf.add_page()
    
    texto_seguro_pdf = limpiar_emojis_para_pdf(texto_markdown)
    lineas = texto_seguro_pdf.split('\n')
    
    pdf.set_font("Arial", 'B', 15)
    pdf.set_text_color(30, 41, 59)
    pdf.cell(0, 10, f"APUNTES DE ESTUDIO: {asignatura}", 0, 1, 'L')
    pdf.set_font("Arial", 'I', 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Nivel académico adaptado: {nivel}", 0, 1, 'L')
    pdf.ln(5)
    
    pdf.set_font("Arial", size=10)
    pdf.set_text_color(30, 41, 59)
    
    for linea in lineas:
        linea_limpia = linea.strip()
        if not linea_limpia:
            pdf.ln(3)
            continue
            
        if linea_limpia.startswith("# "):
            pdf.ln(4)
            pdf.set_font("Arial", 'B', 13)
            pdf.set_text_color(227, 82, 5)
            pdf.multi_cell(0, 7, linea_limpia.replace("# ", ""))
            pdf.set_text_color(30, 41, 59)
            pdf.set_font("Arial", size=10)
            pdf.ln(2)
        elif linea_limpia.startswith("## "):
            pdf.ln(3)
            pdf.set_font("Arial", 'B', 11)
            pdf.set_text_color(71, 85, 105)
            pdf.multi_cell(0, 6, linea_limpia.replace("## ", ""))
            pdf.set_text_color(30, 41, 59)
            pdf.set_font("Arial", size=10)
            pdf.ln(2)
        elif linea_limpia.startswith("> "):
            pdf.set_fill_color(255, 248, 240)
            pdf.set_font("Arial", 'I', 10)
            pdf.set_text_color(180, 60, 0)
            texto_caja = linea_limpia.replace("> ", "")
            pdf.multi_cell(0, 6, f"   [IDEA CLAVE] {texto_caja}", 0, 'L', fill=True)
            pdf.set_font("Arial", size=10)
            pdf.set_text_color(30, 41, 59)
            pdf.ln(2)
        elif linea_limpia.startswith("- ") or linea_limpia.startswith("* "):
            pdf.set_font("Arial", size=10)
            pdf.multi_cell(0, 5, f"    {linea_limpia}")
        else:
            pdf.set_font("Arial", size=10)
            pdf.multi_cell(0, 5, linea_limpia)
                
    return pdf.output(dest="S").encode("latin-1")

def limpiar_texto_for_audio(texto):
    texto = re.sub(r'<[^>]+>', ' ', texto)
    texto = re.sub(r'[\*\#\_\[\]\(\)]', ' ', texto)
    return texto.strip()

def limpiar_html_para_markdown(texto):
    if not texto: return ""
    return re.sub(r'<[^>]*>', '', texto)

def obtener_icono_asignatura(nombre):
    nombre_lower = nombre.lower()
    if any(w in nombre_lower for w in ["mate", "calculo", "numeros"]): return "📐", "#2563EB"
    elif any(w in nombre_lower for w in ["lengua", "literatura", "texto", "lectura"]): return "📖", "#7C3AED"
    elif any(w in nombre_lower for w in ["sociales", "historia", "geo"]): return "🌍", "#D97706"
    elif any(w in nombre_lower for w in ["ciencias", "bio", "fisica", "quimica", "tecno"]): return "🔬", "#059669"
    elif any(w in nombre_lower for w in ["ingles", "idioma", "french", "frances"]): return "🗺️", "#DC2626"
    else: return "📚", "#E35205"

def actualizar_apuntes_automaticos(ruta_asignatura, client, instruccion_nivel):
    ruta_json_apuntes = os.path.join(ruta_asignatura, "apuntes_dinamicos.json")
    archivos_actuales = [f for f in os.listdir(ruta_asignatura) if os.path.isfile(os.path.join(ruta_asignatura, f)) and f not in ["fecha_examen.txt", "apuntes_dinamicos.json", "estadisticas.json", "flashcards_leitner.json"]]
    
    if not archivos_actuales:
        if os.path.exists(ruta_json_apuntes): os.remove(ruta_json_apuntes)
        return

    texto_total_material = ""
    for arch in archivos_actuales:
        ruta_f = os.path.join(ruta_asignatura, arch)
        if arch.lower().endswith(".pdf"):
            try:
                lector = PyPDF2.PdfReader(ruta_f)
                for pag in lector.pages: texto_total_material += (pag.extract_text() or "") + "\n"
            except: pass

    if not texto_total_material.strip(): return

    contenido_previo = ""
    if os.path.exists(ruta_json_apuntes):
        try:
            with open(ruta_json_apuntes, "r", encoding="utf-8") as fj:
                contenido_previo = json.load(fj).get("texto", "")
        except: pass

    prompt_automatico = f"""
    {instruccion_nivel}
    Apuntes previos:\n{contenido_previo}\n
    Material completo:\n{texto_total_material}\n
    TAREA: Reconstruye y sintetiza Apuntes Maestros visuales estructurados con títulos (#, ##), listas y cajas de conceptos clave usando bloques de citas (>). Prohibido HTML.
    """
    try:
        res_auto = client.models.generate_content(model='gemini-3.5-flash', contents=prompt_automatico)
        with open(ruta_json_apuntes, "w", encoding="utf-8") as fj:
            json.dump({"texto": limpiar_html_para_markdown(res_auto.text), "ultima_actualizacion": str(datetime.now())}, fj, ensure_ascii=False)
    except: pass

def cargar_stats_asignatura(ruta_asignatura):
    ruta_stats = os.path.join(ruta_asignatura, "estadisticas.json")
    if os.path.exists(ruta_stats):
        try:
            with open(ruta_stats, "r", encoding="utf-8") as f: return json.load(f)
        except: pass
    return {"tests_realizados": 0, "suma_notas": 0.0, "ensayos_entregados": 0}

def guardar_stats_asignatura(ruta_asignatura, stats):
    ruta_stats = os.path.join(ruta_asignatura, "estadisticas.json")
    with open(ruta_stats, "w", encoding="utf-8") as f: json.dump(stats, f, ensure_ascii=False)

# 1. Configuración de página
st.set_page_config(page_title="Campus Educativo Familiar", page_icon="🎓", layout="wide", initial_sidebar_state="expanded")

API_KEY = "AQ.Ab8RN6Ib45rnV8dY1WIEMzLgs0OEOJOUbe64h9iv0KUFPGjLjg" 
client = genai.Client(api_key=API_KEY)
CARPETA_FAMILIAR = "Campus_Familiar_Datos"
os.makedirs(CARPETA_FAMILIAR, exist_ok=True)

st.markdown("""
    <style>
    .stApp { background-color: #FFFFFF !important; color: #1E293B; }
    [data-testid="stSidebar"] { background-color: #FFF3E0 !important; }
    .titulo-principal { color: #E35205 !important; text-align: center; font-size: 3.5em; font-weight: 900; margin-top: 10px; margin-bottom: 5px; }
    .subtitulo { text-align: center; color: #64748B !important; font-size: 1.3em; margin-bottom: 40px; font-weight: 500; }
    div[data-testid="stButton"] > button { background-color: #E35205 !important; color: #FFFFFF !important; border-radius: 8px !important; border: none !important; font-weight: bold !important; padding: 0.6rem 1.2rem !important; box-shadow: 0 4px 6px rgba(227, 82, 5, 0.2) !important; }
    div[data-testid="stButton"] > button p { color: #FFFFFF !important; font-weight: bold !important; font-size: 1.1em !important; }
    div[data-testid="stButton"] > button:hover { background-color: #1E293B !important; transform: translateY(-2px); }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; border-bottom: 2px solid #FFE0B2; flex-wrap: wrap; }
    .stTabs [data-baseweb="tab"] { background-color: transparent; border: none; padding: 10px 15px; }
    .stTabs [aria-selected="true"] { border-bottom: 4px solid #E35205 !important; background-color: #FFF3E0 !important; border-radius: 8px 8px 0 0; }
    .logro-box { background-color: white; border-left: 5px solid #E35205; padding: 12px; margin-bottom: 10px; border-radius: 5px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    .file-card { background: white; border: 1px solid #E2E8F0; border-radius: 10px; padding: 15px; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,0.02); margin-bottom: 10px; }
    blockquote { border-left: 5px solid #E35205 !important; background-color: #FFF8F0 !important; padding: 15px !important; border-radius: 0 8px 8px 0 !important; margin: 20px 0 !important; }
    </style>
""", unsafe_allow_html=True)

# =====================================================================
# GESTOR DE PERFILES EDITABLES Y CURSOS DINÁMICOS
# =====================================================================
with st.sidebar:
    st.markdown("""
        <div style="background: linear-gradient(135deg, #E35205 0%, #FF7A00 100%); padding: 20px; border-radius: 15px; text-align: center; box-shadow: 0 4px 10px rgba(227,82,5,0.3); margin-bottom: 15px;">
            <h1 style="color: white; margin: 0; font-size: 2.5em; font-weight: 900; letter-spacing: 1px; font-family: sans-serif;">CAMPUS</h1>
            <p style="color: white; margin: 0; font-size: 0.75em; font-weight: 600; opacity: 0.9;">FAMILIAR MULTI-ESTUDIANTE</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("### 👤 Seleccionar Perfil")
    
    perfiles_existentes = [d for d in os.listdir(CARPETA_FAMILIAR) if os.path.isdir(os.path.join(CARPETA_FAMILIAR, d))]
    if not perfiles_existentes:
        perfiles_existentes = ["Papá (Universidad)"]
        os.makedirs(os.path.join(CARPETA_FAMILIAR, "Papá (Universidad)"), exist_ok=True)
        json.dump({"nivel": "Universidad (VIU)"}, open(os.path.join(CARPETA_FAMILIAR, "Papá (Universidad)", "meta.json"), "w"))

    perfil_seleccionado = st.selectbox("Usuario activo:", perfiles_existentes, label_visibility="collapsed")
    
    # --- CREAR NUEVO PERFIL ---
    with st.expander("➕ Añadir Nuevo Estudiante"):
        nuevo_nombre = st.text_input("Nombre:")
        etapa_educativa = st.selectbox("Etapa:", ["Primaria", "ESO", "Bachillerato", "Universidad (VIU)"])
        
        if etapa_educativa == "Primaria":
            curso_det = st.selectbox("Curso:", ["1º de Primaria", "2º de Primaria", "3º de Primaria", "4º de Primaria", "5º de Primaria", "6º de Primaria"])
            rama_det = ""
        elif etapa_educativa == "ESO":
            curso_det = st.selectbox("Curso:", ["1º de ESO", "2º de ESO", "3º de ESO", "4º de ESO"])
            rama_det = ""
        elif etapa_educativa == "Bachillerato":
            curso_det = st.selectbox("Curso:", ["1º de Bachillerato", "2º de Bachillerato"])
            rama_det = st.selectbox("Modalidad / Rama:", ["Ciencias y Tecnología", "Humanidades y Ciencias Sociales", "Ciencias de la Salud"])
        else:
            curso_det = "Grado Universitario"
            rama_det = ""

        if st.button("Crear Perfil Estudiante"):
            if nuevo_nombre:
                nombre_carpeta = f"{nuevo_nombre} ({curso_det}" + (f" - {rama_det})" if rama_det else ")")
                path_nuevo = os.path.join(CARPETA_FAMILIAR, nombre_carpeta)
                os.makedirs(path_nuevo, exist_ok=True)
                meta_data = {"etapa": etapa_educativa, "curso": curso_det, "rama": rama_det, "nivel_completo": nombre_carpeta}
                json.dump(meta_data, open(os.path.join(path_nuevo, "meta.json"), "w", encoding="utf-8"))
                st.toast(f"¡Perfil de {nuevo_nombre} creado!", icon="✅")
                time.sleep(1); st.rerun()

    # --- EDITAR O BORRAR PERFIL ACTUAL ---
    with st.expander("⚙️ Administrar Perfil Actual"):
        st.write(f"Editando: **{perfil_seleccionado}**")
        path_perfil_actual = os.path.join(CARPETA_FAMILIAR, perfil_seleccionado)
        meta_path_actual = os.path.join(path_perfil_actual, "meta.json")
        
        # Leemos datos previos
        datos_meta = {}
        if os.path.exists(meta_path_actual):
            try: datos_meta = json.load(open(meta_path_actual, "r", encoding="utf-8"))
            except: pass
            
        edit_nombre = st.text_input("Cambiar Nombre:", value=perfil_seleccionado.split(" (")[0])
        edit_etapa = st.selectbox("Cambiar Etapa:", ["Primaria", "ESO", "Bachillerato", "Universidad (VIU)"], index=["Primaria", "ESO", "Bachillerato", "Universidad (VIU)"].index(datos_meta.get("etapa", "Universidad (VIU)")) if datos_meta.get("etapa") in ["Primaria", "ESO", "Bachillerato", "Universidad (VIU)"] else 3)
        
        if edit_etapa == "Primaria":
            edit_curso = st.selectbox("Cambiar Curso:", ["1º de Primaria", "2º de Primaria", "3º de Primaria", "4º de Primaria", "5º de Primaria", "6º de Primaria"])
            edit_rama = ""
        elif edit_etapa == "ESO":
            edit_curso = st.selectbox("Cambiar Curso:", ["1º de ESO", "2º de ESO", "3º de ESO", "4º de ESO"])
            edit_rama = ""
        elif edit_etapa == "Bachillerato":
            edit_curso = st.selectbox("Cambiar Curso:", ["1º de Bachillerato", "2º de Bachillerato"])
            edit_rama = st.selectbox("Cambiar Rama:", ["Ciencias y Tecnología", "Humanidades y Ciencias Sociales", "Ciencias de la Salud"])
        else:
            edit_curso = "Grado Universitario"
            edit_rama = ""

        col_ed1, col_ed2 = st.columns(2)
        if col_ed1.button("💾 Guardar Cambios"):
            nuevo_nombre_carpeta = f"{edit_nombre} ({edit_curso}" + (f" - {edit_rama})" if edit_rama else ")")
            nuevo_path = os.path.join(CARPETA_FAMILIAR, nuevo_nombre_carpeta)
            meta_data_nueva = {"etapa": edit_etapa, "curso": edit_curso, "rama": edit_rama, "nivel_completo": nuevo_nombre_carpeta}
            
            if path_perfil_actual != nuevo_path:
                if os.path.exists(nuevo_path): shutil.rmtree(nuevo_path)
                shutil.move(path_perfil_actual, nuevo_path)
            
            json.dump(meta_data_nueva, open(os.path.join(nuevo_path, "meta.json"), "w", encoding="utf-8"))
            st.toast("¡Perfil actualizado con éxito!", icon="🔄")
            time.sleep(1); st.rerun()
            
        if col_ed2.button("🗑️ Borrar Perfil", type="primary"):
            if len(perfiles_existentes) > 1:
                shutil.rmtree(path_perfil_actual)
                st.toast("Perfil eliminado", icon="🧹")
                time.sleep(1); st.rerun()
            else:
                st.error("No puedes borrar el único perfil activo.")

    # Carpeta base exclusiva del usuario actual
    CARPETA_BASE = os.path.join(CARPETA_FAMILIAR, perfil_seleccionado)
    os.makedirs(CARPETA_BASE, exist_ok=True)

    # Cargamos el nivel dinámico actual para la IA
    meta_path = os.path.join(CARPETA_BASE, "meta.json")
    nivel_actual_ia = perfil_seleccionado # por defecto usamos el nombre de carpeta
    if os.path.exists(meta_path):
        try:
            m_dat = json.load(open(meta_path, "r", encoding="utf-8"))
            nivel_actual_ia = m_dat.get("nivel_completo", perfil_seleccionado)
        except: pass

    # MATRIZ PEDAGÓGICA DINÁMICA (IA MIRANDO EL CURSO EXACTO)
    if "Primaria" in nivel_actual_ia:
        instruccion_nivel = f"""
        Actúa como un profesor excelente, paciente y muy didáctico especializado en educación primaria. 
        El alumno cursa actualmente: {nivel_actual_ia}. 
        OBLIGATORIO: Adapta el vocabulario, las explicaciones, los ejemplos y la complejidad de los ejercicios a un niño/a de este curso escolar exacto. Usa tono motivador, sencillo y claro.
        """
        icono_nivel = "🎒"
    elif "ESO" in nivel_actual_ia:
        instruccion_nivel = f"""
        Actúa como un profesor de instituto brillante, claro y estructurado. 
        El alumno cursa actualmente: {nivel_actual_ia}. 
        OBLIGATORIO: Adapta el rigor académico, los conceptos y la profundidad al nivel exacto de educación secundaria obligatoria de este curso, evitando lenguaje excesivamente universitario pero manteniendo exigencia escolar.
        """
        icono_nivel = "🎒"
    elif "Bachillerato" in nivel_actual_ia:
        instruccion_nivel = f"""
        Actúa como un catedrático de instituto preparatorio para la universidad / EBAU. 
        El alumno cursa actualmente: {nivel_actual_ia}. 
        OBLIGATORIO: Alto rigor analítico, demostraciones formales, terminología técnica adecuada a la modalidad de Bachillerato elegida (Ciencias, Letras o Salud) y enfoque selectivo riguroso.
        """
        icono_nivel = "🏛️"
    else:
        instruccion_nivel = f"""
        Actúa como un profesor universitario experto. 
        El usuario cursa actualmente estudios superiores ({nivel_actual_ia}). 
        OBLIGATORIO: Rigor académico absoluto, bases metodológicas, fuentes críticas y terminología científica/humanística de postgrado.
        """
        icono_nivel = "🎓"

    # Sesión independiente por usuario
    if "usuario_activo" not in st.session_state or st.session_state.usuario_activo != perfil_seleccionado:
        st.session_state.usuario_activo = perfil_seleccionado
        st.session_state.mensajes = []
        st.session_state.archivos_activos = []
        st.session_state.asignatura_actual = None
        st.session_state.xp = 0

    st.markdown("---")
    st.markdown(f"### {icono_nivel} Curso: {nivel_actual_ia}")
    
    ruta_xp_user = os.path.join(CARPETA_BASE, "xp_logros.json")
    if "xp" not in st.session_state:
        if os.path.exists(ruta_xp_user):
            try: st.session_state.xp = json.load(open(ruta_xp_user, "r")).get("xp", 0)
            except: st.session_state.xp = 0
        else: st.session_state.xp = 0

    def guardar_xp():
        json.dump({"xp": st.session_state.xp}, open(os.path.join(CARPETA_BASE, "xp_logros.json"), "w"))

    nivel_xp = (st.session_state.xp // 100) + 1
    progreso_xp = st.session_state.xp % 100
    st.progress(progreso_xp / 100, text=f"Progreso Nivel {nivel_xp} - {progreso_xp}/100 XP")

    st.markdown("---")
    st.write("☕ **Pomodoro Familiar**")
    components.html("""
        <div style="text-align:center; font-family:sans-serif; padding:10px; background:white; border:2px solid #FFE0B2; border-radius:10px;">
            <h1 id="timer" style="color:#E35205; margin:0; font-size:2em; font-weight:900;">25:00</h1>
            <button onclick="startTimer()" style="padding:4px 10px; border:none; background:#E35205; color:white; border-radius:5px; cursor:pointer; font-weight:bold; margin-right:5px;">▶️</button>
            <button onclick="resetTimer()" style="padding:4px 10px; border:1px solid #1E293B; background:white; color:#1E293B; border-radius:5px; cursor:pointer; font-weight:bold;">🔄</button>
            <script>
                let time = 1500; let timer; let running = false;
                function updateDisplay() { let m = Math.floor(time/60).toString().padStart(2,'0'); let s = (time%60).toString().padStart(2,'0'); document.getElementById('timer').innerText = m + ":" + s; }
                function startTimer() { if(running) return; running = true; timer = setInterval(() => { if(time <= 0) { clearInterval(timer); running = false; alert("¡Descanso!"); return; } time--; updateDisplay(); }, 1000); }
                function resetTimer() { clearInterval(timer); running = false; time = 1500; updateDisplay(); }
            </script>
        </div>
    """, height=110)
    
    st.divider()
    usar_internet = st.toggle("🌐 Búsqueda Global (Red)", value=False)
    
    st.write(f"📁 **Añadir Asignatura**")
    nueva_asig = st.text_input("Nombre de la asignatura:", label_visibility="collapsed")
    if st.button("➕ Crear Asignatura"):
        if nueva_asig:
            os.makedirs(os.path.join(CARPETA_BASE, nueva_asig), exist_ok=True)
            st.toast(f"¡Asignatura '{nueva_asig}' creada!", icon="✅")
            st.session_state.xp += 10; guardar_xp(); time.sleep(1); st.rerun()

if usar_internet: regla_contexto = "Usa los documentos aportados como base, pero BUSCA libremente en la red."
else: regla_contexto = "Basándote ÚNICAMENTE Y ESTRICTAMENTE en los documentos aportados."

carpetas = [f for f in os.listdir(CARPETA_BASE) if os.path.isdir(os.path.join(CARPETA_BASE, f))]

# =====================================================================
# PANTALLA PRINCIPAL (DASHBOARD)
# =====================================================================
if st.session_state.asignatura_actual is None:
    st.markdown(f'<p class="titulo-principal">Campus Educativo Familiar</p>', unsafe_allow_html=True)
    st.markdown(f'<p class="subtitulo">Estudiante activo: <b>{perfil_seleccionado}</b></p>', unsafe_allow_html=True)
    
    with st.expander("📖 MANUAL MAESTRO: Sistema Multi-Estudiante Dinámico"):
        st.markdown(f"""
        ¡Bienvenido al **Campus Familiar Dinámico**! 
        * **Adaptación de Curso Real:** La IA analiza en tiempo real el curso exacto seleccionado (**{nivel_actual_ia}**). Si tu hija pasa de 4º a 5º de Primaria, o de 1º a 2º de ESO, solo tienes que ir a *⚙️ Administrar Perfil Actual* en el menú lateral y actualizar su curso.
        * **Bachillerato Especializado:** Si eliges Bachillerato, puedes indicar si es de *Ciencias*, *Letras* o *Salud*, ajustando las explicaciones científicas o humanísticas correspondientes.
        * **Independencia Total:** Cada miembro de la familia tiene sus asignaturas, sus notas medias en tests y su progresión con Tito.
        """)
    st.write("---")

    if not carpetas:
        st.warning(f"👈 No hay asignaturas creadas para {perfil_seleccionado}. Añade una en el menú lateral.")
    else:
        st.markdown("### 📚 Asignaturas del Estudiante:")
        cols = st.columns(3)
        for i, carpeta in enumerate(carpetas):
            icono, color = obtener_icono_asignatura(carpeta)
            ruta_asig_temp = os.path.join(CARPETA_BASE, carpeta)
            stats_temp = cargar_stats_asignatura(ruta_asig_temp)
            nota_media = round(stats_temp["suma_notas"] / stats_temp["tests_realizados"], 2) if stats_temp["tests_realizados"] > 0 else "Sin evaluar"
            
            with cols[i % 3]:
                st.markdown(f"""
                    <div style="background: white; border-top: 5px solid {color}; padding: 20px; border-radius: 12px; box-shadow: 0 4px 6px rgba(0,0,0,0.05); text-align: center; margin-bottom: 15px;">
                        <div style="font-size: 2.5em; margin-bottom: 5px;">{icono}</div>
                        <h3 style="color: #1E293B; margin: 0; font-size: 1.2em;">{carpeta}</h3>
                        <p style="color: #64748B; font-size: 0.9em; margin-top: 8px;">📊 Nota Media Test: <b>{nota_media}</b></p>
                    </div>
                """, unsafe_allow_html=True)
                if st.button(f"Entrar en {carpeta}", key=f"btn_{carpeta}", use_container_width=True):
                    st.session_state.asignatura_actual = carpeta
                    st.rerun()

# =====================================================================
# ZONA DE ESTUDIO (DENTRO DE UNA ASIGNATURA)
# =====================================================================
else:
    asignatura = st.session_state.asignatura_actual
    ruta_asignatura = os.path.join(CARPETA_BASE, asignatura)
    icono_asig, _ = obtener_icono_asignatura(asignatura)
    
    stats_asig = cargar_stats_asignatura(ruta_asignatura)
    
    col_back, col_title, col_del = st.columns([1, 3, 1])
    with col_back:
        if st.button("⬅️ Volver", use_container_width=True):
            st.session_state.asignatura_actual = None; st.rerun()
    with col_title:
        st.markdown(f"<h2 style='text-align: center; color: #E35205;'>{icono_asig} {asignatura}</h2>", unsafe_allow_html=True)
    with col_del:
        with st.expander("⚙️ Opciones"):
            if st.button("🗑️ Eliminar asignatura", use_container_width=True):
                shutil.rmtree(ruta_asignatura); st.session_state.asignatura_actual = None; st.rerun()
    
    st.divider()
    
    media_asignatura = round(stats_asig["suma_notas"] / stats_asig["tests_realizados"], 2) if stats_asig["tests_realizados"] > 0 else 0.0
    col_s1, col_s2, col_s3 = st.columns(3)
    col_s1.metric("📊 Nota Media en Tests", f"{media_asignatura} / 10")
    col_s2.metric("🎯 Tests Realizados", stats_asig["tests_realizados"])
    col_s3.metric("📜 Trabajos Evaluados", stats_asig["ensayos_entregados"])
    st.write("---")

    archivo_subido = st.file_uploader("📎 Sube apuntes, temarios o ejercicios", type=["pdf", "mp3", "wav", "m4a"])
    if archivo_subido:
        with open(os.path.join(ruta_asignatura, archivo_subido.name), "wb") as f: f.write(archivo_subido.getbuffer())
        with st.status(f"🪄 Adaptando apuntes al nivel {nivel_actual_ia}...", expanded=True) as status:
            actualizar_apuntes_automaticos(ruta_asignatura, client, instruccion_nivel)
            status.update(label="¡Apuntes actualizados!", state="complete", expanded=False)
        st.toast("¡Archivo guardado!", icon="💾")
        st.session_state.xp += 8; guardar_xp(); st.rerun()

    archivos_guardados = [f for f in os.listdir(ruta_asignatura) if os.path.isfile(os.path.join(ruta_asignatura, f)) and f not in ["fecha_examen.txt", "apuntes_dinamicos.json", "estadisticas.json", "flashcards_leitner.json"]]
    
    # =========================================================================
    # PESTAÑAS DE ESTUDIO MAESTRO
    # =========================================================================
    tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8 = st.tabs([
        "📚 Apuntes", "📝 Evaluador", "💬 Chat Tutor", "🎯 Test", "✍️ Ejercicios", "👨‍🏫 Audio Explicativo", "🌐 Esquema Visual", "🗂️ Leitner"
    ])
    
    # --- 1: APUNTES DINÁMICOS CON DESCARGA GRÁFICA EN PDF ---
    with tab1:
        st.markdown(f"##### 📚 Apuntes Dinámicos ({nivel_actual_ia})")
        ruta_json_apuntes = os.path.join(ruta_asignatura, "apuntes_dinamicos.json")
        if os.path.exists(ruta_json_apuntes):
            with open(ruta_json_apuntes, "r", encoding="utf-8") as fj: datos_apuntes = json.load(fj)
            
            c1, c2 = st.columns([2, 1])
            c1.write(f"🕒 *Adaptado a: {nivel_actual_ia}*")
            
            pdf_bytes_grafico = generar_pdf_grafico_ilustrado(datos_apuntes["texto"], asignatura, nivel_actual_ia)
            c2.download_button("🎨 Descargar PDF Gráfico", data=pdf_bytes_grafico, file_name=f"Apuntes_{asignatura}.pdf", mime="application/pdf", use_container_width=True)
            
            st.write("---")
            st.markdown(limpiar_html_para_markdown(datos_apuntes["texto"]))
        else:
            if archivos_guardados and st.button("🪄 Generar Apuntes", type="primary"):
                actualizar_apuntes_automaticos(ruta_asignatura, client, instruccion_nivel); st.rerun()
            st.info("💡 Sube un archivo PDF para generar los apuntes adaptados a tu curso.")

    # --- 2: EVALUADOR DE TRABAJOS / DEBERES ---
    with tab2:
        st.markdown(f"##### 📝 Evaluador de Trabajos y Deberes ({nivel_actual_ia})")
        st.write("Pega tu redacción o trabajo para recibir correcciones y nota orientada al curso actual.")
        
        texto_trabajo = st.text_area("📄 Pega aquí el contenido:", height=250)
        rubrica_opcional = st.text_area("📋 (Opcional) Enunciado o criterios del profesor:", height=100)
        
        if st.button("⚖️ Evaluar Trabajo", type="primary"):
            if not texto_trabajo.strip(): st.warning("⚠️ El texto está vacío.")
            else:
                with st.status("⚖️ Evaluando según estándares del curso...", expanded=True) as status:
                    prompt_ev = f"""
                    {instruccion_nivel}
                    Evalúa el siguiente trabajo escolar/académico con rigor constructivo. Da una nota del 0 al 10 y explica el porqué. Criterios: {rubrica_opcional if rubrica_opcional else 'Criterios académicos generales del curso'}.
                    TRABAJO: {texto_trabajo}
                    """
                    res_eval = client.models.generate_content(model='gemini-3.5-flash', contents=prompt_ev)
                    status.update(label="¡Evaluado!", state="complete", expanded=False)
                st.write("---")
                st.markdown(res_eval.text)

    # GESTIÓN DE MATERIALES
    if archivos_guardados:
        with st.expander("⚙️ Gestionar Materiales y Selección"):
            archivos_a_borrar = st.multiselect("Archivos a eliminar:", archivos_guardados)
            if archivos_a_borrar and st.button("🗑️ Borrar seleccionados", type="primary"):
                for arch in archivos_a_borrar:
                    p = os.path.join(ruta_asignatura, arch)
                    if os.path.exists(p): os.remove(p)
                    if arch in st.session_state.archivos_activos: st.session_state.archivos_activos.remove(arch)
                actualizar_apuntes_automaticos(ruta_asignatura, client, instruccion_nivel)
                st.rerun()
        
        st.write("---")
        archivos_seleccionados = st.multiselect("📄 Activa archivos para estudiar:", archivos_guardados)
        
        contexto_para_gemini = []
        texto_combinado = ""
        if archivos_seleccionados:
            for archivo in archivos_seleccionados:
                ruta_archivo = os.path.join(ruta_asignatura, archivo)
                if archivo.lower().endswith(".pdf"):
                    lector_pdf = PyPDF2.PdfReader(ruta_archivo)
                    for pagina in lector_pdf.pages: texto_combinado += pagina.extract_text() + "\n"
                else:
                    if archivo not in st.session_state.gemini_files:
                        st.session_state.gemini_files[archivo] = client.files.upload(file=ruta_archivo)
                    contexto_para_gemini.append(st.session_state.gemini_files[archivo])
            if texto_combinado: contexto_para_gemini.append(texto_combinado)

        # --- 3: CHAT ---
        with tab3:
            st.markdown("##### 💬 Chat con Tutor Inteligente")
            if not archivos_seleccionados: st.warning("⚠️ Selecciona archivos.")
            else:
                for m in st.session_state.mensajes:
                    with st.chat_message(m["role"]): st.write(m["content"])
                if pregunta := st.chat_input("Escribe tu pregunta..."):
                    with st.chat_message("user"): st.write(pregunta)
                    st.session_state.mensajes.append({"role": "user", "content": pregunta})
                    historial = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.mensajes])
                    with st.chat_message("assistant"):
                        resp = client.models.generate_content(model='gemini-3.5-flash', contents=list(contexto_para_gemini)+[f"{instruccion_nivel} {regla_contexto} Historial:\n{historial}\nResponde."])
                        st.write(resp.text)
                    st.session_state.mensajes.append({"role": "assistant", "content": resp.text})

        # --- 4: TEST ---
        with tab4:
            st.markdown("##### 🎯 Simulacro de Test / Preguntas")
            if not archivos_seleccionados: st.warning("⚠️ Selecciona archivos.")
            else:
                num_p = st.number_input("Nº preguntas", 3, 15, 5)
                if st.button("🚀 Generar Test"):
                    res_t = client.models.generate_content(model='gemini-3.5-flash', contents=list(contexto_para_gemini)+[f"{instruccion_nivel} {regla_contexto} Crea test de {num_p} preguntas adaptadas al nivel exacto. JSON: [ {{\"pregunta\":\"...\",\"opciones\":[\"A\",\"B\",\"C\",\"D\"],\"respuesta_correcta\":\"...\",\"explicacion\":\"...\"}} ]"])
                    simbolo = chr(96) * 3
                    st.session_state.test_interactivo = json.loads(res_t.text.replace(simbolo + 'json', '').replace(simbolo, '').strip())
                
                if "test_interactivo" in st.session_state:
                    respuestas_u = {}
                    for i, q in enumerate(st.session_state.test_interactivo):
                        st.markdown(f"**{i+1}. {q['pregunta']}**")
                        respuestas_u[i] = st.radio("Respuesta:", q['opciones'], key=f"p_{i}", index=None, label_visibility="collapsed")
                    if st.button("📝 Corregir Test"):
                        aciertos = sum(1 for i, q in enumerate(st.session_state.test_interactivo) if respuestas_u[i] == q['respuesta_correcta'])
                        nota = round(aciertos * (10.0 / len(st.session_state.test_interactivo)), 2)
                        st.metric("Nota Final", f"{nota} / 10")
                        stats_asig["tests_realizados"] += 1; stats_asig["suma_notas"] += nota
                        guardar_stats_asignatura(ruta_asignatura, stats_asig)

        # --- 5: EJERCICIOS ---
        with tab5:
            st.markdown("##### ✍️ Generador de Ejercicios Prácticos")
            if not archivos_seleccionados: st.warning("⚠️ Selecciona archivos.")
            else:
                if st.button("🎲 Proponer Ejercicio"):
                    st.session_state.ejercicio_txt = client.models.generate_content(model='gemini-3.5-flash', contents=list(contexto_para_gemini)+[f"{instruccion_nivel} Genera un ejercicio o problema práctico adaptado a su curso."]).text
                if "ejercicio_txt" in st.session_state:
                    st.info(st.session_state.ejercicio_txt)
                    sol_alu = st.text_area("Tu respuesta:", height=150)
                    if st.button("📤 Corregir Ejercicio"):
                        res_corr = client.models.generate_content(model='gemini-3.5-flash', contents=list(contexto_para_gemini)+[f"{instruccion_nivel} Corrige esta respuesta: {sol_alu}"]).text
                        st.write(res_corr)

        # --- 6: AUDIO EXPLICATIVO ---
        with tab6:
            st.markdown("##### 👨‍🏫 Explicación en Audio")
            if not archivos_seleccionados: st.warning("⚠️ Selecciona archivos.")
            else:
                tema_p = st.text_input("Tema a explicar:")
                if st.button("🎬 Generar Explicación") and tema_p:
                    explicacion_txt = client.models.generate_content(model='gemini-3.5-flash', contents=list(contexto_para_gemini)+[f"{instruccion_nivel} Explica '{tema_p}' de forma amena y adecuada a su edad/curso."]).text
                    st.session_state.explicacion_txt = explicacion_txt
                if "explicacion_txt" in st.session_state:
                    if st.button("🎙️ Escuchar Audio"):
                        tts = gTTS(text=limpiar_texto_for_audio(st.session_state.explicacion_txt), lang='es', tld='es')
                        ab = BytesIO(); tts.write_to_fp(ab)
                        st.audio(ab.getvalue(), format='audio/mp3')
                    st.markdown(st.session_state.explicacion_txt)

        # --- 7: ESQUEMA VISUAL ---
        with tab7:
            st.markdown("##### 🌐 Esquema Conceptual Visual")
            if not archivos_seleccionados: st.warning("⚠️ Selecciona archivos.")
            else:
                if st.button("🗺️ Generar Esquema"):
                    st.session_state.esquema_txt = client.models.generate_content(model='gemini-3.5-flash', contents=list(contexto_para_gemini)+[f"{instruccion_nivel} Crea un esquema conceptual estructurado usando flechas adaptado al nivel."]).text
                if "esquema_txt" in st.session_state: st.markdown(st.session_state.esquema_txt)

        # --- 8: LEITNER ---
        with tab8:
            st.markdown("##### 🗂️ Tarjetas de Memoria (Leitner)")
            ruta_leitner = os.path.join(ruta_asignatura, "flashcards_leitner.json")
            if not os.path.exists(ruta_leitner):
                if st.button("🪄 Generar Tarjetas", type="primary") and archivos_seleccionados:
                    res_l = client.models.generate_content(model='gemini-3.5-flash', contents=list(contexto_para_gemini)+[f"{instruccion_nivel} Extrae 8 conceptos clave adaptados al nivel. JSON: [ {{\"c\": \"Concepto\", \"d\": \"Definición\"}} ]"])
                    simbolo = chr(96) * 3
                    cards_ini = json.loads(res_l.text.replace(simbolo + 'json', '').replace(simbolo, '').strip())
                    for c in cards_ini: c["caja"] = 1
                    with open(ruta_leitner, "w", encoding="utf-8") as f: json.dump(cards_ini, f, ensure_ascii=False)
                    st.rerun()
            
            if os.path.exists(ruta_leitner):
                with open(ruta_leitner, "r", encoding="utf-8") as f: cards = json.load(f)
                caja_filtro = st.selectbox("Selecciona Caja:", ["🔴 Caja 1", "🟡 Caja 2", "🟢 Caja 3"])
                num_caja = 1 if "Caja 1" in caja_filtro else (2 if "Caja 2" in caja_filtro else 3)
                filtradas = [c for c in cards if c.get("caja", 1) == num_caja]
                
                for idx, card in enumerate(filtradas):
                    with st.expander(f"❓ {card['c']}"):
                        st.markdown(f"Respuesta:")
                        col_l1, col_l2, col_l3 = st.columns(3)
                        if col_l1.button("🔴 Caja 1", key=f"l1_{num_caja}_{idx}"):
                            card["caja"] = 1; json.dump(cards, open(ruta_leitner, "w", encoding="utf-8"), ensure_ascii=False); st.rerun()
                        if col_l2.button("🟡 Caja 2", key=f"l2_{num_caja}_{idx}"):
                            card["caja"] = 2; json.dump(cards, open(ruta_leitner, "w", encoding="utf-8"), ensure_ascii=False); st.rerun()
                        if col_l3.button("🟢 Caja 3", key=f"l3_{num_caja}_{idx}"):
                            card["caja"] = 3; json.dump(cards, open(ruta_leitner, "w", encoding="utf-8"), ensure_ascii=False); st.rerun()
            else:
                st.info("💡 Genera tarjetas para empezar a repasar.")