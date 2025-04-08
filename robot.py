import io
import os
import tempfile
import streamlit as st
import google.generativeai as genai
import speech_recognition as sr
from gtts import gTTS
from PIL import Image
from PyPDF2 import PdfReader

# --- Streamlit Page Setup ---
st.set_page_config(page_title="AI Learning Companion", page_icon="🤖", layout="wide")
st.title("🤖 TuterX")
st.caption("Your personalized tutor for Math, Physics, and Chemistry")

# --- Gemini API Configuration ---
api_key = "AIzaSyAlyUyF1sX8gN3KgPJyl30QsN4b8pKLTdA"  # Replace with your Gemini API key

if api_key == "YOUR_API_KEY_HERE":
    st.warning("Please provide your Gemini API key.", icon="🔑")
    gemini_configured = False
else:
    try:
        genai.configure(api_key=api_key)
        latest_model_name = 'gemini-1.5-pro-latest'
        text_model = genai.GenerativeModel(latest_model_name)
        vision_model = genai.GenerativeModel(latest_model_name)
        gemini_configured = True
    except Exception as e:
        st.error(f"Error configuring Gemini API: {e}", icon="🚨")
        gemini_configured = False

# --- Personalization Settings ---
st.sidebar.header("Personalization")

language_options = {
    "English": "en",
    "Spanish": "es",
    "French": "fr",
    "German": "de",
    "Japanese": "ja",
    "Hindi": "hi",
    "Telugu": "te"
}

selected_language_name = st.sidebar.selectbox("Select Language:", options=list(language_options.keys()))
selected_lang_code = language_options[selected_language_name]

speed_options = ["Standard", "Simplified", "Detailed"]
selected_speed = st.sidebar.selectbox("Select Explanation Speed:", options=speed_options)

grade_level = st.sidebar.selectbox("Select Grade Level:", options=[f"Grade {i}" for i in range(6, 13)] + ["University"])

# --- Helper Functions ---
def get_tts_audio_bytes(text, lang_code):
    if not text:
        return None
    try:
        tts = gTTS(text=text, lang=lang_code, slow=False)
        audio_fp = io.BytesIO()
        tts.write_to_fp(audio_fp)
        audio_fp.seek(0)
        return audio_fp.read()
    except Exception as e:
        st.warning(f"Could not generate audio ({lang_code}): {e}", icon="🔊")
        return None

def get_text_response(prompt, grade, speed, lang_name, lang_code):
    if not gemini_configured:
        return "Error: Gemini API not configured."

    speed_instruction = ""
    if speed == "Simplified":
        speed_instruction = "Explain in very simple terms, using basic vocabulary."
    elif speed == "Detailed":
        speed_instruction = "Provide highly detailed, step-by-step explanations."

    educational_context = f"""
    You are an AI Tutor assisting a student whose grade level is '{grade}'.
    The student prefers explanations in '{lang_name}'. Respond only in '{lang_name}'.
    Explanation speed: '{speed}'. {speed_instruction}
    Subjects: Mathematics, Physics, Chemistry.
    Provide clear, age-appropriate, step-by-step explanations with relevant examples.
    Question: {prompt}
    Answer in {lang_name}:
    """

    try:
        response = text_model.generate_content(
            educational_context,
            generation_config=genai.types.GenerationConfig(temperature=0.7)
        )
        return response.text
    except Exception as e:
        st.error(f"Error generating response: {e}", icon="🔥")
        return "Sorry, there was an error generating the response."

def analyze_image(image_file, prompt):
    if not gemini_configured:
        return "Error: Gemini API not configured."
    try:
        image_data = image_file.getvalue()
        image = Image.open(io.BytesIO(image_data))
        response = vision_model.generate_content([prompt, image])
        return response.text
    except Exception as e:
        st.error(f"Error analyzing image: {e}", icon="🔥")
        return "Sorry, there was an error analyzing the image."

def analyze_pdf(pdf_file, prompt):
    if not gemini_configured:
        return "Error: Gemini API not configured."
    try:
        pdf_reader = PdfReader(pdf_file)
        text = ""
        for page_num in range(len(pdf_reader.pages)):
            page = pdf_reader.pages[page_num]
            text += page.extract_text()
        if text:
            context = f"""Analyze the content of the following PDF and answer the question:
            PDF Content:
            {text}
            Question: {prompt}
            Answer in {selected_language_name}:
            """
            response = text_model.generate_content(context)
            return response.text
        else:
            return "Could not extract text from the PDF. Please ensure it contains selectable text."
    except Exception as e:
        st.error(f"Error analyzing PDF: {e}", icon="🔥")
        return "Sorry, there was an error analyzing the PDF."

def recognize_from_microphone():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("Listening... Speak now")
        try:
            audio = recognizer.listen(source)
        except sr.WaitTimeoutError:
            return "No speech detected."
    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return "Sorry, I could not understand the audio."
    except sr.RequestError as e:
        return f"Could not request results from Google Speech Recognition service; {e}"

# --- State Management ---
if "voice_input" not in st.session_state:
    st.session_state.voice_input = ""
if "show_camera" not in st.session_state:
    st.session_state.show_camera = False

# --- Input UI ---
st.markdown("""
<style>
.stTextInput > div > div > input {
    padding-right: 5.5rem !important;
}
</style>
""", unsafe_allow_html=True)

prompt_container = st.container()
with prompt_container:
    col_prompt, col_mic, col_cam = st.columns([0.8, 0.1, 0.1])
    with col_prompt:
        prompt = st.text_input(
            "Ask something or describe the file...",
            key="chat_input",
            value=st.session_state.voice_input,
            label_visibility="collapsed",
        )
        if st.session_state.voice_input:
            st.session_state.voice_input = ""

    with col_mic:
        if st.button("🎤", help="Click to speak", key="mic_button", use_container_width=True):
            spoken_text = recognize_from_microphone()
            st.session_state.voice_input = spoken_text
            st.rerun()

    with col_cam:
        if st.button("📷", help="Capture from webcam", key="camera_button", use_container_width=True):
            st.session_state.show_camera = True
            st.rerun()

# --- Webcam Input ---
if st.session_state.get("show_camera", False):
    captured_image = st.camera_input("Take a picture with your webcam")
    if captured_image:
        st.session_state.show_camera = False
        if prompt:
            with st.spinner("Analyzing webcam image..."):
                response_text = analyze_image(captured_image, prompt)
                st.subheader("Webcam Image Analysis Result:")
                st.markdown(response_text)
                audio_bytes = get_tts_audio_bytes(response_text, selected_lang_code)
                if audio_bytes:
                    st.audio(audio_bytes, format="audio/mp3")
        else:
            st.warning("Please enter a question or description for the captured image.")

# --- File Upload Section ---
uploaded_files = st.file_uploader("Upload images or PDFs for analysis:", type=["png", "jpg", "jpeg", "pdf"], accept_multiple_files=True)

if uploaded_files:
    for uploaded_file in uploaded_files:
        file_type = uploaded_file.type
        file_name = uploaded_file.name
        st.subheader(f"Analyzing: {file_name}")

        if prompt:
            if "image" in file_type:
                with st.spinner(f"Analyzing image '{file_name}'..."):
                    response_text = analyze_image(uploaded_file, prompt)
                    st.subheader("Analysis Result:")
                    st.markdown(response_text)
                    audio_bytes = get_tts_audio_bytes(response_text, selected_lang_code)
                    if audio_bytes:
                        st.audio(audio_bytes, format="audio/mp3")
            elif "pdf" in file_type:
                with st.spinner(f"Analyzing PDF '{file_name}'..."):
                    response_text = analyze_pdf(uploaded_file, prompt)
                    st.subheader("Analysis Result:")
                    st.markdown(response_text)
                    audio_bytes = get_tts_audio_bytes(response_text, selected_lang_code)
                    if audio_bytes:
                        st.audio(audio_bytes, format="audio/mp3")
            else:
                st.warning(f"Unsupported file type: {file_type}")
        else:
            st.warning("Please provide a description or question related to the uploaded file.")

elif prompt and not uploaded_files:
    st.write(f"You asked: {prompt}")
    if gemini_configured:
        with st.spinner(f"Generating response in {selected_language_name}..."):
            response_text = get_text_response(prompt, grade_level, selected_speed, selected_language_name, selected_lang_code)
            st.subheader("Answer:")
            st.markdown(response_text)
            audio_bytes = get_tts_audio_bytes(response_text, selected_lang_code)
            if audio_bytes:
                st.audio(audio_bytes, format="audio/mp3")

# --- Footer ---
st.sidebar.markdown("---")
