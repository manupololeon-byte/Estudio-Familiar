import streamlit as st
import os
from pathlib import Path

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
        border-radius: 8px;
        border: none;
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #C2410C;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

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

# --- GESTIÓN DE PERFILES Y ASIGNATURAS ---
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
    
    # Menú de navegación interno
    menu = st.sidebar.radio("Navegación", ["📚 Asignaturas y Materiales", "✍️ Súper Exámenes Pro", "🤖 Tutor IA & Podcast"])

    if menu == "📚 Asignaturas y Materiales":
        st.subheader("Gestión de Asignaturas")
        col1, col2 = st.columns([3, 1])
        with col1:
            nueva_asig = st.text_input("Nueva Asignatura", label_visibility="collapsed", placeholder="Ej. Historia Antigua / Matemáticas")
        with col2:
            if st.button("➕ Añadir"):
                if nueva_asig:
                    (ruta_perfil / nueva_asig).mkdir(exist_ok=True)
                    st.success("Asignatura creada")
                    st.rerun()

        asignaturas = [d.name for d in ruta_perfil.iterdir() if d.is_dir()]
        if asignaturas:
            asig_elegida = st.selectbox("Selecciona Asignatura para ver Materiales", asignaturas)
            ruta_asig = ruta_perfil / asig_elegida
            
            st.markdown("---")
            st.write(f"📂 Materiales para: **{asig_elegida}**")
            
            # Subir PDFs o Audios
            archivos_subidos = st.file_uploader("Sube tus apuntes (PDF o Audio MP3/M4A)", type=["pdf", "mp3", "m4a", "wav"], accept_multiple_files=True)
            if archivos_subidos:
                for archivo in archivos_subidos:
                    ruta_archivo = ruta_asig / archivo.name
                    with open(ruta_archivo, "wb") as f:
                        f.write(archivo.getbuffer())
                st.success("¡Materiales guardados correctamente!")

            # Listar materiales existentes
            materiales = [f.name for f in ruta_asig.iterdir() if f.is_file()]
            if materiales:
                st.write("📄 **Archivos en esta asignatura:**")
                for mat in materiales:
                    st.text(f"• {mat}")
            else:
                st.info("No hay archivos subidos todavía.")

    elif menu == "✍️ Súper Exámenes Pro":
        st.subheader("🎯 Creador de Exámenes Maestros")
        asignaturas = [d.name for d in ruta_perfil.iterdir() if d.is_dir()]
        
        if not asignaturas:
            st.warning("Primero crea alguna asignatura y sube apuntes.")
        else:
            asig_examen = st.multiselect("Selecciona Asignatura(s) para el Examen", asignaturas)
            
            tipo_examen = st.selectbox("Modalidad de Examen", ["Tipo Test", "Solo Redacción / Desarrollo", "Mixto (Test 50% + Redacción 50%)"])
            
            num_preguntas = st.slider("Número de preguntas (Tipo Test)", 10, 100, 20)
            
            penaliza = False
            if "Test" in tipo_examen or "Mixto" in tipo_examen:
                penaliza = st.checkbox("¿Las respuestas incorrectas restan 0,25 puntos?")

            if st.button("🚀 Generar Examen Pro"):
                if not asig_examen:
                    st.error("Selecciona al menos una asignatura.")
                else:
                    st.success(f"¡Examen generado con éxito! (Modalidad: {tipo_examen}, Preguntas: {num_preguntas}, Penalización: {'Sí (-0.25)' if penaliza else 'No'})")
                    # Aquí conectaremos el motor de IA en el siguiente bloque

    elif menu == "🤖 Tutor IA & Podcast":
        st.subheader("🤖 Tutor de Historia / Académico & Podcast")
        st.info("Próximamente: Chat tutor adaptado al nivel (Universidad / Primaria / CyL) y generación de audios explicativos.")
