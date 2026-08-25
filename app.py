import streamlit as st
import os
from pathlib import Path
from google import genai

st.set_page_config(
    page_title="Campus Educativo Familiar",
    page_icon="🐾",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Estilos CSS de alta gama: tarjetas flotantes, colores suaves y diseño amable
st.markdown("""
    <style>
    .main { background-color: #F8FAFC; }
    .chopi-card {
        background: linear-gradient(135deg, #FFF3E0 0%, #FFE0B2 100%);
        border: 1px solid #FFCC80;
        padding: 18px;
        border-radius: 14px;
        margin-bottom: 20px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.03);
    }
    .card-asignatura {
        background: white;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        margin-bottom: 15px;
    }
    .apunte-box {
        background-color: white;
        border-left: 6px solid #E35205;
        padding: 22px;
        border-radius: 10px;
        box-shadow: 0 3px 6px rgba(0,0,0,0.04);
        margin-top: 15px;
        margin-bottom: 15px;
    }
    .stButton>button {
        background-color: #E35205;
        color: white;
        border-radius: 8px;
        border: none;
        font-weight: bold;
        padding: 8px 16px;
    }
    .stButton>button:hover {
        background-color: #C2410C;
        color: white;
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
    st.session_state.xp = 150
if "asig_actual" not in st.session_state:
    st.session_state.asig_actual = None

# Función auxiliar para streaming ultra rápido con el nuevo SDK de Gemini
def stream_generacion(prompt_text):
    response = client.models.generate_content_stream(
        model='gemini-3.5-flash',
        contents=prompt_text
    )
    for chunk in response:
        if chunk.text:
            yield chunk.text

# --- MASCOTA CHOPI Y RECOMPENSAS ---
def obtener_estado_chopi(xp):
    nivel = (xp // 100) + 1
    if xp < 250:
        return f"🐶 Chopi (Nivel {nivel}) - ¡Qué ganas de hincar los codos en el iPad!", "🟢 Alegre", "#E35205"
    elif xp < 600:
        return f"🌟 Chopi (Nivel {nivel}) - ¡Imparable! ¡Estás bordando los exámenes!", "🔥 Estelar", "#D97706"
    else:
        return f"👑 Chopi (Nivel {nivel}) - ¡Catedrático Canino Supremo! ¡Nivel Dios!", "💎 Legendario", "#7C3AED"

texto_chopi, estado_txt, color_chopi = obtener_estado_chopi(st.session_state.xp)

st.markdown(f"""
    <div class="chopi-card">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <h4 style="margin: 0; color: #1E293B;">🐾 Chopi - Tu Compañero de Estudio</h4>
            <span style="background: {color_chopi}; color: white; padding: 4px 10px; border-radius: 20px; font-size: 12px; font-weight: bold;">{estado_txt} (XP: {st.session_state.xp})</span>
        </div>
        <p style="margin: 8px 0 0 0; color: #475569; font-size: 14px;">{texto_chopi}</p>
    </div>
""", unsafe_allow_html=True)

st.title("🎓 Campus Educativo Familiar & Historia")

if not client:
    st.error("⚠️ Falta configurar la `GEMINI_API_KEY` en los Secrets de Streamlit Cloud.")

perfiles = [d.name for d in CARPETA_FAMILIAR.iterdir() if d.is_dir()]

if not perfiles:
    st.info("Crea tu primer perfil de estudiante:")
    nuevo_perfil = st.text_input("Nombre del Estudiante")
    if st.button("Crear Perfil"):
        if nuevo_perfil:
            (CARPETA_FAMILIAR / nuevo_perfil).mkdir(exist_ok=True)
            st.rerun()
else:
    perfil_activo = st.selectbox("👤 Usuario Activo", perfiles)
    ruta_perfil = CARPETA_FAMILIAR / perfil_activo

    # --- CONTROL DE NAVEGACIÓN: SI ESTAMOS DENTRO DE UNA ASIGNATURA O EN EL GENERAL ---
    if st.session_state.asig_actual is None:
        # PANTALLA PRINCIPAL DE ASIGNATURAS
        st.subheader("📚 Mis Asignaturas")
        
        col1, col2 = st.columns([3, 1])
        with col1:
            nueva_asig = st.text_input("Nombre de Asignatura", label_visibility="collapsed", placeholder="Ej. Historia de España / Geografía")
        with col2:
            if st.button("➕ Crear Asignatura"):
                if nueva_asig:
                    (ruta_perfil / nueva_asig).mkdir(exist_ok=True)
                    st.success("¡Asignatura creada!")
                    st.rerun()

        asignaturas = [d.name for d in ruta_perfil.iterdir() if d.is_dir()]
        
        if not asignaturas:
            st.info("No hay asignaturas creadas todavía. Añade una arriba para empezar.")
        else:
            st.markdown("---")
            for asig in asignaturas:
                st.markdown(f"""
                    <div class="card-asignatura">
                        <h3 style="margin: 0 0 10px 0; color: #1E293B;">📚 {asig}</h3>
                    </div>
                """, unsafe_allow_html=True)
                
                col_btn1, col_btn2 = st.columns([2, 2])
                with col_btn1:
                    if st.button(f"📂 Entrar a la Asignatura", key=f"entrar_{asig}"):
                        st.session_state.asig_actual = asig
                        st.rerun()
                with col_btn2:
                    if st.button(f"🗑️ Borrar Asignatura", key=f"borrar_asig_{asig}"):
                        import shutil
                        shutil.rmtree(ruta_perfil / asig)
                        st.rerun()

    else:
        # --- PÁGINA ESPECÍFICA DE LA ASIGNATURA ---
        asig_elegida = st.session_state.asig_actual
        ruta_asig = ruta_perfil / asig_elegida

        if st.button("⬅️ Volver al listado general de asignaturas"):
            st.session_state.asig_actual = None
            st.rerun()

        st.markdown(f"## 📚 Asignatura: {asig_elegida}")
        
        tab_materiales, tab_apuntes, tab_examenes, tab_tutor = st.tabs(["📂 Materiales y Carpetas", "✨ Apuntes Dinámicos", "🎯 Súper Exámenes Pro", "🤖 Tutor IA"])

        with tab_materiales:
            st.subheader("Gestión de Materiales y Apartados")
            
            sub_carpeta = st.text_input("Crear apartado o carpeta (ej. Tema 1 - Prehistoria)")
            if st.button("➕ Crear Carpeta"):
                if sub_carpeta:
                    (ruta_asig / sub_carpeta).mkdir(exist_ok=True)
                    st.success("Carpeta creada")
                    st.rerun()

            carpetas = [d.name for d in ruta_asig.iterdir() if d.is_dir()]
            carpeta_elegida = st.selectbox("Selecciona carpeta / apartado", ["Raíz (General)"] + carpetas)
            
            ruta_destino = ruta_asig if carpeta_elegida == "Raíz (General)" else ruta_asig / carpeta_elegida

            archivos_subidos = st.file_uploader(f"Sube archivos a [{carpeta_elegida}] (PDF, MP3, M4A)", type=["pdf", "mp3", "m4a", "wav"], accept_multiple_files=True)
            if archivos_subidos:
                for archivo in archivos_subidos:
                    with open(ruta_destino / archivo.name, "wb") as f:
                        f.write(archivo.getbuffer())
                st.success("¡Archivos subidos con éxito!")
                st.rerun()

            st.markdown("### 📄 Archivos en este apartado:")
            ficheros_actuales = [f.name for f in ruta_destino.iterdir() if f.is_file()]
            if ficheros_actuales:
                for f in ficheros_actuales:
                    col_f1, col_f2 = st.columns([4, 1])
                    with col_f1:
                        st.text(f"• {f}")
                    with col_f2:
                        if st.button("🗑️", key=f"del_f_{f}"):
                            (ruta_destino / f).unlink()
                            st.rerun()
            else:
                st.info("No hay archivos en este apartado.")

        # --- PESTAÑA APUNTES CON STREAMING FLUIDO ---
        with tab_apuntes:
            st.subheader("Apuntes Dinámicos, Visuales y Descargables")
            
            todos_los_archivos = [f.name for f in ruta_asig.glob("**/*") if f.is_file()]
            
            if todos_los_archivos:
                if client and st.button("✨ Actualizar Apuntes Visuales Automáticamente"):
                    prompt_apuntes = f"""
                    Actúa como un catedrático de Historia. Genera apuntes académicos altamente **visuales, estructurados y atractivos** para la asignatura {asig_elegida}, basándote en los archivos: {', '.join(todos_los_archivos)}.
                    Utiliza tablas, esquemas conceptuales en texto y tarjetas destacadas.
                    """
                    # Generación palabra por palabra inmediata
                    contenedor_apuntes = st.empty()
                    with contenedor_apuntes.container():
                        st.markdown("**Generando apuntes en tiempo real...**")
                        texto_completo = st.write_stream(stream_generacion(prompt_apuntes))
                        st.session_state[f"apuntes_{asig_elegida}"] = texto_completo
                        st.session_state.xp += 25
                        st.rerun()

            if f"apuntes_{asig_elegida}" in st.session_state:
                st.markdown(f"""
                    <div class="apunte-box">
                        {st.session_state[f"apuntes_{asig_elegida}"]}
                    </div>
                """, unsafe_allow_html=True)

                st.download_button(
                    label="📥 Exportar Apuntes a PDF / TXT",
                    data=st.session_state[f"apuntes_{asig_elegida}"],
                    file_name=f"Apuntes_{asig_elegida}.txt",
                    mime="text/plain"
                )
            else:
                st.info("Sube archivos en la pestaña anterior para generar los apuntes dinámicos.")

        # --- PESTAÑA EXÁMENES CON STREAMING ---
        with tab_examenes:
            st.subheader("🎯 Creador de Exámenes Maestros & Calibración 0-10")
            
            tipo_examen = st.selectbox("Modalidad de Examen", ["Tipo Test", "Solo Redacción / Desarrollo", "Mixto (Test 50% + Redacción 50%)"])
            num_preguntas = st.slider("Número de preguntas (Tipo Test)", 10, 100, 20)
            
            penaliza = False
            if "Test" in tipo_examen or "Mixto" in tipo_examen:
                penaliza = st.checkbox("¿Las respuestas incorrectas restan 0,25 puntos?")

            if st.button("🚀 Lanzar Examen Pro") and client:
                prompt_ex = f"""
                Crea un examen formal de nivel académico para la asignatura {asig_elegida}.
                Modalidad: {tipo_examen}. Número de preguntas tipo test: {num_preguntas}. 
                Penalización por fallo: {'Sí (-0.25)' if penaliza else 'No'}.
                Incluye sus respectivas respuestas o criterios de corrección al final.
                """
                st.markdown("**Redactando examen...**")
                examen_completo = st.write_stream(stream_generacion(prompt_ex))
                st.session_state[f"examen_{asig_elegida}"] = examen_completo
                st.session_state.xp += 25
                st.rerun()

            if f"examen_{asig_elegida}" in st.session_state:
                st.markdown("---")
                st.markdown(st.session_state[f"examen_{asig_elegida}"])
                
                st.markdown("### 🏆 Calificación del Examen")
                nota_simulada = st.slider("Asigna tu nota ponderada final (0 a 10)", 0.0, 10.0, 5.0, 0.25)
                if st.button("💾 Guardar Nota y Recompensar a Chopi"):
                    st.session_state.xp += 50
                    st.success(f"¡Nota guardada: {nota_simulada} / 10! Chopi ha ganado +50 XP por tu esfuerzo.")
                    st.rerun()

        # --- PESTAÑA TUTOR CON STREAMING ---
        with tab_tutor:
            st.subheader("🤖 Tutor Académico Personalizado")
            pregunta = st.text_input("Hazle cualquier consulta al tutor de Historia sobre esta asignatura:")
            if pregunta and client:
                st.write_stream(stream_generacion(f"Como tutor académico experto en {asig_elegida}, responde de forma rigurosa y visual a: {pregunta}"))
