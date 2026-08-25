import os
import streamlit as st
import google.generativeai as genai

# Configuración de página optimizada para iPad/Desktop
st.set_page_config(page_title="Campus de Estudio IA", page_icon="🎓", layout="wide")

# Inicializar API Key
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    API_KEY = st.sidebar.text_input("Introduce tu Gemini API Key:", type="password")

if API_KEY:
    genai.configure(api_key=API_KEY)
    # Modelo 3.5 Flash configurado
    model = genai.GenerativeModel("gemini-3.5-flash")
else:
    st.warning("Introduce tu API Key en la barra lateral para comenzar.")
    st.stop()

# Estado de sesión (Mascota Chopi y XP)
if "xp" not in st.session_state:
    st.session_state.xp = 0
if "nivel" not in st.session_state:
    st.session_state.nivel = 1

def sumar_xp(puntos):
    st.session_state.xp += puntos
    st.session_state.nivel = (st.session_state.xp // 100) + 1

# Generador con Streaming para evitar bloqueos y pantallas congeladas
def stream_gemini_response(prompt_text):
    response = model.generate_content(prompt_text, stream=True)
    for chunk in response:
        if chunk.text:
            yield chunk.text

# Barra lateral: Perfil y Mascota
with st.sidebar:
    st.header("🐾 Compañero Chopi")
    st.metric("Nivel", st.session_state.nivel)
    st.progress(min((st.session_state.xp % 100) / 100, 1.0))
    st.caption(f"XP actual: {st.session_state.xp} / {(st.session_state.nivel) * 100}")
    
    st.markdown("---")
    modo = st.radio(
        "Herramienta:",
        ["Generador de Apuntes", "Motor de Exámenes", "Tutor IA"]
    )

# 1. GENERADOR DE APUNTES
if modo == "Generador de Apuntes":
    st.subheader("📚 Generador Dinámico de Apuntes")
    tema = st.text_input("Tema o materia a desarrollar:")
    detalles = st.text_area("Puntos clave o contenido base (opcional):")
    
    if st.button("Generar Apuntes"):
        if tema:
            prompt = f"Genera unos apuntes estructurados, claros y rigurosos a nivel universitario sobre: {tema}.\nDetalles adicionales: {detalles}"
            st.info("Generando contenido en tiempo real...")
            st.write_stream(stream_gemini_response(prompt))
            sumar_xp(25)
            st.success("¡Apuntes generados! (+25 XP)")
        else:
            st.error("Por favor, introduce un tema.")

# 2. MOTOR DE EXÁMENES
elif modo == "Motor de Exámenes":
    st.subheader("📝 Generador de Exámenes y Autoevaluación")
    materia = st.text_input("Materia / Tema del examen:")
    num_preguntas = st.slider("Número de preguntas:", min_value=3, max_value=20, value=5)
    
    if st.button("Crear Cuestionario"):
        if materia:
            prompt = f"Genera un examen de autoevaluación con {num_preguntas} preguntas tipo test (4 opciones) con sus soluciones justificadas al final sobre: {materia}."
            st.write_stream(stream_gemini_response(prompt))
            sumar_xp(35)
            st.success("¡Examen listo! (+35 XP)")
        else:
            st.error("Indica la materia.")

# 3. TUTOR IA
elif modo == "Tutor IA":
    st.subheader("💬 Consulta con el Tutor")
    if "mensajes_tutor" not in st.session_state:
        st.session_state.mensajes_tutor = []

    for msg in st.session_state.mensajes_tutor:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if duda := st.chat_input("Escribe tu pregunta académica..."):
        st.session_state.mensajes_tutor.append({"role": "user", "content": duda})
        with st.chat_message("user"):
            st.markdown(duda)

        with st.chat_message("assistant"):
            respuesta_stream = stream_gemini_response(duda)
            respuesta_completa = st.write_stream(respuesta_stream)
        
        st.session_state.mensajes_tutor.append({"role": "assistant", "content": respuesta_completa})
        sumar_xp(10)
