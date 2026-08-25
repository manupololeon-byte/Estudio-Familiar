import streamlit as st
import os
import threading
from pathlib import Path
from google import genai

st.set_page_config(
    page_title="Campus Educativo Familiar",
    page_icon="🐕‍🦺",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos visuales refinados y animación para Chopi
st.markdown("""
    <style>
    .main { background-color: #F8FAFC; font-family: 'Segoe UI', system-ui, sans-serif; }
    
    @keyframes floatPet {
        0% { transform: translateY(0px) scale(1); }
        50% { transform: translateY(-6px) scale(1.02); }
        100% { transform: translateY(0px) scale(1); }
    }
    .chopi-card {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        border: 2px solid #F59E0B;
        color: white;
        padding: 20px;
        border-radius: 16px;
        margin-bottom: 25px;
        box-shadow: 0 10px 20px rgba(0,0,0,0.12);
        display: flex;
        align-items: center;
        gap: 18px;
    }
    .chopi-avatar {
        font-size: 52px;
        animation: floatPet 3s ease-in-out infinite;
        background: #334155;
        border-radius: 50%;
        padding: 10px 14px;
        border: 2px solid #F59E0B;
    }
    .card-asig {
        background: white;
        padding: 20px;
        border-radius: 14px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.05);
        text-align: center;
    }
    .stButton>button {
        background-color: #E35205;
        color: white;
        border-radius: 10px;
        border: none;
        font-weight: 600;
        padding: 8px 18px;
    }
    .stButton>button:hover {
        background-color: #C2410C;
        color: white;
    }
    .hero-banner {
        background: linear-gradient(135deg, #FFF7ED 0%, #FFEDD5 100%);
        border-left: 6px solid #EA580C;
        padding: 24px;
        border-radius: 14px;
        margin-bottom: 25px;
    }
    .apunte-box {
        background-color: white;
        border-left: 6px solid #E35205;
        padding: 24px;
        border-radius: 12px;
        box-shadow: 0 4px 8px rgba(0,0,0,0.04);
        margin: 15px 0;
    }
    </style>
""", unsafe_allow_html=True)

try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)
except Exception:
    client = None

CARPETA_FAMILIAR = Path("Campus_Familiar_Datos")
CARPETA_FAMILIAR.mkdir(exist_ok=True)

if "xp" not in st.session_state:
    st.session_state.xp = 180
if "asig_actual" not in st.session_state:
    st.session_state.asig_actual = None
if "tareas_background" not in st.session_state:
    st.session_state.tareas_background = {}
if "nivel_educativo" not in st.session_state:
    st.session_state.nivel_educativo = "Universidad"

def obtener_icono_asig(nombre):
    n = nombre.lower()
    if any(k in n for k in ["geo", "tierra", "mapa"]): return "🌍"
    if any(k in n for k in ["historia", "arte", "patrimonio", "antigua", "roma"]): return "🏛️"
    if any(k in n for k in ["lengua", "literatura", "idioma", "latin"]): return "📖"
    if any(k in n for k in ["mate", "algebra", "calculo", "fisica"]): return "📐"
    if any(k in n for k in ["bio", "ciencias", "naturales", "quimica"]): return "🧬"
    if any(k in n for k in ["filo", "etica", "pensamiento"]): return "💡"
    if any(k in n for k in ["ingles", "frances", "english"]): return "🗣️"
    if any(k in n for k in ["musica", "audio"]): return "🎵"
    return "📚"

# Función de trabajo asíncrono con control de fuentes (archivos vs currículo)
def trabajador_apuntes_fondo(api_key, asig_nombre, nivel_edu, ampliar_web, tema_manual, rutas_archivos, dict_estado):
    try:
        dict_estado["estado"] = "running"
        dict_estado["progreso"] = "Analizando fuentes de estudio..."
        
        cliente_thread = genai.Client(api_key=api_key)
        archivos_remotos = []
        for ruta in rutas_archivos:
            if ruta.suffix.lower() in [".mp3", ".m4a", ".wav", ".pdf"]:
                subido = cliente_thread.files.upload(file=str(ruta))
                archivos_remotos.append(subido)
        
        # Construcción del prompt según perfil educativo
        if "Castilla y León" in nivel_edu:
            instruccion_fuente = f"""
            ESTUDIANTE ESCOLAR ({nivel_edu}):
            - Aplica con total fidelidad el CURRÍCULO OFICIAL DE CASTILLA Y LEÓN (BOCYL / LOMLOE).
            - Desarrolla el tema '{asig_nombre}' {f'- Apartado: {tema_manual}' if tema_manual else ''} basándote en los saberes básicos, competencias y criterios de evaluación de este curso escolar.
            - No es necesario que dependas de archivos subidos, ya que el alumno utiliza libros físicos. Genera apuntes didácticos, con explicaciones claras, tablas y vocabulario adaptado a su edad.
            """
        else:
            # Modo Universitario (VIU)
            if ampliar_web or not archivos_remotos:
                instruccion_fuente = f"""
                ESTUDIANTE UNIVERSITARIO:
                - Asignatura: '{asig_nombre}' {f'- Tema: {tema_manual}' if tema_manual else ''}.
                - Rigor de Grado Universitario. Sintetiza los archivos proporcionados y AMPLÍA con bibliografía académica, debates historiográficos y contexto general.
                """
            else:
                instruccion_fuente = f"""
                ESTUDIANTE UNIVERSITARIO (MODO ESTRICTO DE MATERIALES):
                - Asignatura: '{asig_nombre}'.
                - ATENCIÓN: Extrae y sintetiza la información ÚNICA Y EXCLUSIVAMENTE de los archivos y audios de clase adjuntos. No añadas información externa no mencionada en las clases o documentos.
                """

        prompt = f"""
        {instruccion_fuente}
        
        Estructura los apuntes de forma visual, organizada con títulos claros, tablas comparativas y puntos clave destacados.
        """
        
        dict_estado["progreso"] = "Chopi está redactando los apuntes estructurados..."
        res = cliente_thread.models.generate_content(
            model='gemini-3.5-flash',
            contents=[prompt] + archivos_remotos
        )
        
        dict_estado["resultado"] = res.text
        dict_estado["estado"] = "done"
    except Exception as e:
        dict_estado["estado"] = "error"
        dict_estado["resultado"] = f"Error: {str(e)}"

def obtener_estado_chopi(xp):
    nivel = (xp // 100) + 1
    if xp < 250:
        return f"¡Guau! Soy Chopi (Patterdale Terrier). Listo para estudiar.", "🟢 Activo", "#10B981"
    elif xp < 600:
        return f"¡Gran ritmo de estudio! Estamos devorando el temario.", "⚡ En Racha", "#F59E0B"
    else:
        return f"¡Catedrático Canino Supremo! Dominio absoluto de la materia.", "👑 Experto", "#8B5CF6"

texto_chopi, estado_txt, color_chopi = obtener_estado_chopi(st.session_state.xp)

# --- CABECERA CON CHOPI ---
col_chopi, col_premio = st.columns([4, 1])
with col_chopi:
    st.markdown(f"""
        <div class="chopi-card">
            <div class="chopi-avatar">🐕‍🦺</div>
            <div>
                <div style="display: flex; gap: 10px; align-items: center;">
                    <h3 style="margin: 0; color: #F8FAFC;">Chopi</h3>
                    <span style="background: {color_chopi}; color: white; padding: 2px 10px; border-radius: 12px; font-size: 12px; font-weight: bold;">
                        Nivel {(st.session_state.xp // 100) + 1} | {estado_txt} (XP: {st.session_state.xp})
                    </span>
                </div>
                <p style="margin: 6px 0 0 0; color: #CBD5E1; font-size: 14px;">{texto_chopi}</p>
            </div>
        </div>
    """, unsafe_allow_html=True)

with col_premio:
    st.markdown("<div style='height: 15px;'></div>", unsafe_allow_html=True)
    if st.button("🍖 Dar Premio"):
        st.session_state.xp += 15
        st.balloons()
        st.success("¡+15 XP!")

# --- BARRA LATERAL ---
with st.sidebar:
    st.header("⚙️ Perfil Académico")
    st.session_state.nivel_educativo = st.selectbox(
        "Nivel del Estudiante:",
        ["Universidad", "Bachillerato (Castilla y León)", "ESO (Castilla y León)", "Primaria (Castilla y León)"]
    )
    
    if "Castilla y León" in st.session_state.nivel_educativo:
        st.info("📚 **Modo Escolar CyL:** Diseñado para libros físicos. La IA recurre al currículo oficial de CyL sin necesidad de escanear libros.")
    else:
        st.info("🎓 **Modo Universitario:** Centrado en tus PDFs y audios de clase de la VIU.")
    
    st.markdown("---")
    st.header("⚡ Tareas en Segundo Plano")
    hay_tareas = False
    for asig_k, info_t in st.session_state.tareas_background.items():
        if info_t.get("estado") == "running":
            hay_tareas = True
            st.warning(f"⏳ **{asig_k}**: {info_t.get('progreso')}")
        elif info_t.get("estado") == "done":
            st.success(f"✅ **{asig_k}**: ¡Completado!")
    if not hay_tareas:
        st.caption("Sin procesos activos.")

# --- GESTIÓN DE PERFILES ---
perfiles = [d.name for d in CARPETA_FAMILIAR.iterdir() if d.is_dir()]

if not perfiles:
    st.info("Crea el primer perfil para empezar:")
    nuevo_perfil = st.text_input("Nombre del Estudiante")
    if st.button("Crear Perfil"):
        if nuevo_perfil:
            (CARPETA_FAMILIAR / nuevo_perfil).mkdir(exist_ok=True)
            st.rerun()
else:
    col_u1, col_u2 = st.columns([3, 1])
    with col_u1:
        perfil_activo = st.selectbox("👤 Estudiante:", perfiles)
    with col_u2:
        with st.popover("➕ Añadir Estudiante"):
            otro_perfil = st.text_input("Nombre:")
            if st.button("Guardar"):
                if otro_perfil:
                    (CARPETA_FAMILIAR / otro_perfil).mkdir(exist_ok=True)
                    st.rerun()

    ruta_perfil = CARPETA_FAMILIAR / perfil_activo

    # --- NAVEGACIÓN ---
    if st.session_state.asig_actual is None:
        st.markdown(f"""
            <div class="hero-banner">
                <h2 style="margin:0 0 10px 0; color: #9A3412;">Campus de Estudio de {perfil_activo}</h2>
                <p style="margin:0; color: #431407; font-size: 15px;">
                    • <b>Tus clases de la VIU:</b> Sube audios de 2 horas y PDFs; la IA se ceñirá a ellos.<br>
                    • <b>Colegio e Instituto:</b> Generación directa con el <b>currículo oficial de Castilla y León</b> para estudiar sin tener que escanear libros físicos.
                </p>
            </div>
        """, unsafe_allow_html=True)

        st.subheader(f"📚 Asignaturas")
        col_c1, col_c2 = st.columns([3, 1])
        with col_c1:
            nueva_asig = st.text_input("Nueva Asignatura", label_visibility="collapsed", placeholder="Ej. Historia de España, Geografía 2º ESO...")
        with col_c2:
            if st.button("➕ Crear Asignatura"):
                if nueva_asig:
                    (ruta_perfil / nueva_asig).mkdir(exist_ok=True)
                    st.rerun()

        asignaturas = [d.name for d in ruta_perfil.iterdir() if d.is_dir()]
        if not asignaturas:
            st.info("Añade una asignatura para empezar.")
        else:
            cols = st.columns(3)
            for idx, asig in enumerate(asignaturas):
                icono = obtener_icono_asig(asig)
                with cols[idx % 3]:
                    st.markdown(f"""
                        <div class="card-asig">
                            <div style="font-size: 38px; margin-bottom: 8px;">{icono}</div>
                            <h4 style="margin: 0 0 10px 0; color: #1E293B;">{asig}</h4>
                        </div>
                    """, unsafe_allow_html=True)
                    col_b1, col_b2 = st.columns([3, 1])
                    if col_b1.button("📂 Entrar", key=f"entrar_{asig}", use_container_width=True):
                        st.session_state.asig_actual = asig
                        st.rerun()
                    if col_b2.button("🗑️", key=f"del_asig_{asig}"):
                        import shutil
                        shutil.rmtree(ruta_perfil / asig)
                        st.rerun()

    else:
        asig_elegida = st.session_state.asig_actual
        ruta_asig = ruta_perfil / asig_elegida
        icono_actual = obtener_icono_asig(asig_elegida)

        if st.button("⬅️ Volver al listado"):
            st.session_state.asig_actual = None
            st.rerun()

        st.markdown(f"## {icono_actual} {asig_elegida}")
        tab_mat, tab_ap, tab_ex, tab_tut = st.tabs(["📂 Materiales", "✨ Apuntes Inteligentes", "🎯 Exámenes", "🤖 Tutor IA"])

        with tab_mat:
            st.subheader("Archivos y Grabaciones")
            archivos_subidos = st.file_uploader("Sube audios (hasta 2h) o PDFs:", type=["pdf", "mp3", "m4a", "wav"], accept_multiple_files=True)
            if archivos_subidos:
                for archivo in archivos_subidos:
                    with open(ruta_asig / archivo.name, "wb") as f:
                        f.write(archivo.getbuffer())
                st.success("Archivos guardados correctamente.")
                st.rerun()

            ficheros = [f for f in ruta_asig.glob("*") if f.is_file()]
            if ficheros:
                for f in ficheros:
                    cf1, cf2 = st.columns([4, 1])
                    cf1.text(f"• {f.name} ({round(f.stat().st_size / (1024*1024), 2)} MB)")
                    if cf2.button("🗑️", key=f"delf_{f.name}"):
                        f.unlink()
                        st.rerun()
            else:
                st.caption("No hay archivos subidos. (En modos escolares de CyL no es obligatorio subir nada).")

        with tab_ap:
            st.subheader("Generador de Apuntes")
            es_universidad = "Universidad" in st.session_state.nivel_educativo
            
            ampliar_web = False
            tema_especifico = ""
            
            if es_universidad:
                st.markdown("🔒 **Modo estricto activo:** Se extraerá únicamente la información de tus documentos y audios de clase.")
                ampliar_web = st.checkbox("🌐 Permitir a la IA ampliar con bibliografía general e internet")
            else:
                st.markdown("🏛️ **Modo Curricular CyL:** Desarrollará el temario oficial del curso sin necesidad de escanear libros.")
                tema_especifico = st.text_input("Tema o bloque concreto a desarrollar (ej. 'Tema 3: El Clima y la Vegetación'):")

            ficheros_asig = [f for f in ruta_asig.glob("*") if f.is_file()]
            tarea = st.session_state.tareas_background.get(asig_elegida, {})
            estado = tarea.get("estado", "idle")

            if estado == "running":
                st.info(f"⏳ **Chopi está procesando la tarea en segundo plano.** Puedes hacer exámenes mientras tanto.")
                if st.button("🔄 Comprobar Estado"):
                    st.rerun()
            else:
                if st.button("🚀 Generar Apuntes (En Segundo Plano)"):
                    if client:
                        st.session_state.tareas_background[asig_elegida] = {"estado": "running", "resultado": "", "progreso": "Iniciando..."}
                        hilo = threading.Thread(
                            target=trabajador_apuntes_fondo,
                            args=(API_KEY, asig_elegida, st.session_state.nivel_educativo, ampliar_web, tema_especifico, ficheros_asig, st.session_state.tareas_background[asig_elegida]),
                            daemon=True
                        )
                        hilo.start()
                        st.rerun()

            if estado == "done":
                st.session_state[f"apuntes_{asig_elegida}"] = tarea.get("resultado")

            if f"apuntes_{asig_elegida}" in st.session_state:
                st.markdown(f"""
                    <div class="apunte-box">
                        {st.session_state[f"apuntes_{asig_elegida}"]}
                    </div>
                """, unsafe_allow_html=True)
                st.download_button("📥 Descargar Apuntes (.txt)", data=st.session_state[f"apuntes_{asig_elegida}"], file_name=f"Apuntes_{asig_elegida}.txt")

        with tab_ex:
            st.subheader("🎯 Creador de Exámenes")
            modalidad = st.selectbox("Tipo:", ["Test", "Desarrollo", "Mixto"])
            cant_preg = st.slider("Preguntas:", 5, 30, 10)
            
            if st.button("Crear Examen"):
                if client:
                    with st.spinner("Generando examen calibrado..."):
                        prompt_ex = f"""
                        Genera un examen de {modalidad} con {cant_preg} preguntas para {asig_elegida}.
                        Nivel: {st.session_state.nivel_educativo} (si es escolar, respeta los criterios de evaluación de Castilla y León; si es universitario, rigor académico).
                        Incluye soluciones detalladas al final.
                        """
                        res = client.models.generate_content(model='gemini-3.5-flash', contents=prompt_ex)
                        st.session_state[f"examen_{asig_elegida}"] = res.text
                        st.session_state.xp += 30
                        st.rerun()

            if f"examen_{asig_elegida}" in st.session_state:
                st.markdown(st.session_state[f"examen_{asig_elegida}"])

        with tab_tut:
            st.subheader("🤖 Tutor Particular")
            duda = st.text_input("Formula tu consulta académica:")
            if duda and client:
                with st.spinner("Consultando..."):
                    res = client.models.generate_content(
                        model='gemini-3.5-flash',
                        contents=f"Responde como docente especializado en {asig_elegida} para nivel {st.session_state.nivel_educativo}: {duda}"
                    )
                    st.markdown(res.text)
