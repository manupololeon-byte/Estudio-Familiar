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

st.markdown("""
    <style>
    .main { background-color: #F8FAFC; }
    .chopi-card {
        background-color: #FFF3E0;
        border: 1px solid #FFE0B2;
        padding: 15px;
        border_radius: 10px;
        margin-bottom: 20px;
    }
    .stButton>button {
        background-color: #E35205;
        color: white;
        border_radius: 8px;
        border: none;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #C2410C;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# --- CONFIGURACIÓN SEGURA DE GEMINI ---
try:
    API_KEY = st.secrets["GEMINI_API_KEY"]
    client = genai.Client(api_key=API_KEY)
except Exception:
    client = None

CARPETA_FAMILIAR = Path("Campus_Familiar_Datos")
CARPETA_FAMILIAR.mkdir(exist_ok=True)

if "xp" not in st.session_state:
    st.session_state.xp = 150

# --- MASCOTA CHOPI ---
def obtener_estado_chopi(xp):
    nivel = (xp // 100) + 1
    if xp < 200:
        return f"🐶 Chopi (Nivel {nivel}) - ¡Listos para estudiar en el iPad!", "🟢 Alegre"
    elif xp < 500:
        return f"🌟 Chopi (Nivel {nivel}) - ¡Imparable con los exámenes!", "🔥 Estelar"
    else:
        return f"👑 Chopi (Nivel {nivel}) - ¡Catedrático Canino Supremo!", "💎 Legendario"

texto_chopi, _ = obtener_estado_chopi(st.session_state.xp)
st.markdown(f"""
    <div class="chopi-card">
        <h4 style="margin: 0; color: #1E293B;">🐾 Chopi - Tu Compañero de Estudio</h4>
        <p style="margin: 5px 0 0 0; color: #64748B; font-size: 14px;">{texto_chopi}</p>
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
    
    menu = st.sidebar.radio("Navegación", ["📚 Asignaturas y Materiales", "✍️ Súper Exámenes Pro", "🤖 Tutor IA & Podcast"])

    if menu == "📚 Asignaturas y Materiales":
        st.subheader("Gestión de Asignaturas")
        col1, col2 = st.columns([3, 1])
        with col1:
            nueva_asig = st.text_input("Nueva Asignatura", label_visibility="collapsed", placeholder="Ej. Historia Antigua")
        with col2:
            if st.button("➕ Añadir"):
                if nueva_asig:
                    (ruta_perfil / nueva_asig).mkdir(exist_ok=True)
                    st.success("Asignatura creada")
                    st.rerun()

        asignaturas = [d.name for d in ruta_perfil.iterdir() if d.is_dir()]
        if asignaturas:
            asig_elegida = st.selectbox("Selecciona Asignatura", asignaturas)
            ruta_asig = ruta_perfil / asig_elegida
            
            st.markdown("---")
            st.write(f"📂 Materiales para: **{asig_elegida}**")
            
            archivos_subidos = st.file_uploader("Sube tus apuntes (PDF o Audio)", type=["pdf", "mp3", "m4a", "wav"], accept_multiple_files=True)
            if archivos_subidos:
                for archivo in archivos_subidos:
                    ruta_archivo = ruta_asig / archivo.name
                    with open(ruta_archivo, "wb") as f:
                        f.write(archivo.getbuffer())
                st.success("¡Materiales guardados!")

            materiales = [f.name for f in ruta_asig.iterdir() if f.is_file()]
            if materiales:
                st.write("📄 **Archivos disponibles:**")
                for mat in materiales:
                    st.text(f"• {mat}")
                
                if st.button("✨ Generar Apuntes Dinámicos con IA") and client:
                    with st.spinner("Chopi está leyendo y estructurando los apuntes en esquemas visuales..."):
                        prompt_apuntes = f"Actúa como un profesor experto. Genera apuntes visuales, esquemáticos y estructurados con gráficos en texto para la asignatura {asig_elegida}, basándote en que disponemos de estos archivos: {', '.join(materiales)}."
                        
                        # MODELO CORREGIDO A 3.5-flash:
                        respuesta = client.models.generate_content(
                            model='gemini-3.5-flash',
                            contents=prompt_apuntes
                        )
                        st.markdown("### 📋 Apuntes Dinámicos Generados")
                        st.markdown(respuesta.text)
            else:
                st.info("Sube algún archivo para activar los apuntes dinámicos.")

    elif menu == "✍️ Súper Exámenes Pro":
        st.subheader("🎯 Creador de Exámenes Maestros")
        asignaturas = [d.name for d in ruta_perfil.iterdir() if d.is_dir()]
        
        if not asignaturas:
            st.warning("Primero crea alguna asignatura.")
        else:
            asig_examen = st.multiselect("Selecciona Asignatura(s)", asignaturas)
            tipo_examen = st.selectbox("Modalidad", ["Tipo Test", "Solo Redacción / Desarrollo", "Mixto (Test 50% + Redacción 50%)"])
            num_preguntas = st.slider("Número de preguntas (Tipo Test)", 10, 100, 20)
            
            penaliza = False
            if "Test" in tipo_examen or "Mixto" in tipo_examen:
                penaliza = st.checkbox("¿Las respuestas incorrectas restan 0,25 puntos?")

            if st.button("🚀 Generar Examen Pro") and client:
                if not asig_examen:
                    st.error("Selecciona al menos una asignatura.")
                else:
                    with st.spinner("Diseñando examen riguroso..."):
                        prompt_examen = f"Crea un examen de nivel universitario de historia (o adaptado si es primaria/ESO según currículo de Castilla y León) para la(s) asignatura(s) {', '.join(asig_examen)}. Modalidad: {tipo_examen}. Número de preguntas tipo test: {num_preguntas}. Penalización por fallo: {'Sí (-0.25)' if penaliza else 'No'}."
                        
                        res_examen = client.models.generate_content(
                            model='gemini-3.5-flash',
                            contents=prompt_examen
                        )
                        st.markdown("### 📝 Tu Examen Personalizado")
                        st.markdown(res_examen.text)

    elif menu == "🤖 Tutor IA & Podcast":
        st.subheader("🤖 Tutor de Historia & Explicaciones")
        st.info("Escribe tus dudas abajo y el tutor académico te responderá adaptado a tu nivel.")
        
        pregunta_usuario = st.text_input("¿Qué duda tienes sobre los temas?")
        if pregunta_usuario and client:
            with st.spinner("El tutor está redactando la explicación..."):
                resp_tutor = client.models.generate_content(
                    model='gemini-3.5-flash',
                    contents=f"Actúa como tutor académico universitario de Historia (o profesor de apoyo según nivel). Responde de forma didáctica, visual y rigurosa a: {pregunta_usuario}"
                )
                st.markdown(resp_tutor.text)
