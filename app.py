import streamlit as st
import os
from pathlib import Path

# Configuración de la página optimizada para iPad
st.set_page_config(
    page_title="Campus Educativo Familiar",
    page_icon="🐾",
    layout="centered",
    initial_sidebar_state="expanded"
)

# Estilos CSS personalizados para un diseño limpio y moderno
st.markdown("""
    <style>
    .main { background-color: #F8FAFC; }
    .chopi-card {
        background-color: #FFF3E0;
        border: 1px solid #FFE0B2;
        padding: 15px;
        border-radius: 10px;
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

# Directorio de datos local en la nube del proyecto
CARPETA_FAMILIAR = Path("Campus_Familiar_Datos")
CARPETA_FAMILIAR.mkdir(exist_ok=True)

# --- INICIALIZAR ESTADOS ---
if "xp" not in st.session_state:
    st.session_state.xp = 150  # XP inicial para Chopi

# --- MASCOTA CHOPI ---
def obtener_estado_chopi(xp):
    nivel = (xp // 100) + 1
    if xp < 200:
        return f"🐶 Chopi (Nivel {nivel}) - ¡Motivado y listo para estudiar contigo desde el iPad!", "🟢 Alegre"
    elif xp < 500:
        return f"🌟 Chopi (Nivel {nivel}) - ¡Imparable! ¡Menudos notazos estamos sacando!", "🔥 Estelar"
    else:
        return f"👑 Chopi (Nivel {nivel}) - ¡Catedrático Canino Supremo!", "💎 Legendario"

texto_chopi, _ = obtener_estado_chopi(st.session_state.xp)

# Renderizar tarjeta de Chopi
st.markdown(f"""
    <div class="chopi-card">
        <h4 style="margin: 0; color: #1E293B;">🐾 Chopi - Tu Compañero de Estudio</h4>
        <p style="margin: 5px 0 0 0; color: #64748B; font-size: 14px;">{texto_chopi}</p>
    </div>
""", unsafe_allow_html=True)

st.title("🎓 Campus Educativo Familiar & Historia")

# --- GESTIÓN DE PERFILES ---
perfiles = [d.name for d in CARPETA_FAMILIAR.iterdir() if d.is_dir()]

if not perfiles:
    st.info("No hay perfiles creados todavía. Crea el primero para empezar:")
    nuevo_perfil = st.text_input("Nombre del Estudiante / Perfil (ej. Historial_Papa)")
    if st.button("Crear Perfil"):
        if nuevo_perfil:
            (CARPETA_FAMILIAR / nuevo_perfil).mkdir(exist_ok=True)
            st.rerun()
else:
    perfil_activo = st.selectbox("👤 Selecciona el Usuario Activo", perfiles)
    
    ruta_perfil = CARPETA_FAMILIAR / perfil_activo
    asignaturas = [d.name for d in ruta_perfil.iterdir() if d.is_dir()]

    st.markdown("---")
    st.subheader("📚 Gestión de Asignaturas")

    # Crear nueva asignatura
    col1, col2 = st.columns([3, 1])
    with col1:
        nueva_asig = st.text_input("Nueva Asignatura", label_visibility="collapsed", placeholder="Ej. Historia Antigua / Matemáticas ESO")
    with col2:
        if st.button("➕ Añadir"):
            if nueva_asig:
                (ruta_perfil / nueva_asig).mkdir(exist_ok=True)
                st.success(f"Asignatura creada")
                st.rerun()

    # Listar asignaturas
    if not asignaturas:
        st.write("*(Aún no hay asignaturas en este perfil. Añade una arriba)*")
    else:
        for asig in asignaturas:
            with st.container():
                st.markdown(f"""
                    <div style="background: white; padding: 12px; border-radius: 8px; border: 1px solid #E2E8F0; margin-bottom: 8px; display: flex; justify-content: space-between; align-items: center;">
                        <span style="font-weight: bold; color: #1E293B; font-size: 16px;">📚 {asig}</span>
                    </div>
                """, unsafe_allow_html=True)
                
                # Botón de acceso a la asignatura (preparado para el siguiente bloque)
                if st.button(f"Entrar en {asig}", key=f"btn_{asig}"):
                    st.session_state.asig_activa = asig
                    st.toast(f"Has entrado en {asig}")

