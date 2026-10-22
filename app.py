import os
import glob
import shutil
import tempfile
import streamlit as st
import yt_dlp
from yt_dlp.utils import download_range_func

st.set_page_config(
    page_title="MediaStudio Pro",
    page_icon="🎬",
    layout="centered"
)

# Diseño Dark Glassmorphism
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 100%);
        color: #f8fafc;
    }
    h1 {
        background: linear-gradient(90deg, #38bdf8, #818cf8);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800 !important;
        text-align: center;
    }
    div[data-testid="stVerticalBlock"] > div[style*="flex-direction: column"] {
        background: rgba(30, 41, 59, 0.7);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 20px;
    }
    div.stButton > button[kind="primary"] {
        background: linear-gradient(90deg, #0284c7 0%, #4f46e5 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 12px !important;
        padding: 12px 24px !important;
        font-weight: 600 !important;
        width: 100%;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)

def parse_time(texto):
    partes = texto.strip().split(":")
    if len(partes) not in (2, 3) or not all(p.isdigit() for p in partes):
        raise ValueError("Usa el formato MM:SS o HH:MM:SS.")
    nums = [int(p) for p in partes]
    if len(nums) == 2:
        return nums[0] * 60 + nums[1]
    return nums[0] * 3600 + nums[1] * 60 + nums[2]

def fmt_time(segundos):
    segundos = int(segundos or 0)
    h, resto = divmod(segundos, 3600)
    m, s = divmod(resto, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

st.title("🎬 MediaStudio Pro")
st.caption("⚡ Descarga y recorta multimedia en alta velocidad sin publicidad.")

url = st.text_input("🔗 Enlace del video o audio", placeholder="https://www.youtube.com/watch?v=...")

if st.button("🔍 Cargar Datos del Video"):
    if not url.strip():
        st.warning("Por favor ingresa una URL válida.")
    else:
        opts = {
            "quiet": True, 
            "skip_download": True,
            "nocheckcertificate": True,
            "no_warnings": True,
            "extractor_args": {"youtube": {"player_client": ["android", "web"]}}
        }
        try:
            with st.spinner("Obteniendo información del video..."):
                with yt_dlp.YoutubeDL(opts) as ydl:
                    st.session_state["info"] = ydl.extract_info(url.strip(), download=False)
                    st.session_state["url"] = url.strip()
        except Exception as e:
            st.error(f"❌ Error al conectar con YouTube: {e}")

info = st.session_state.get("info")

if info:
    st.divider()
    
    col_thumb, col_details = st.columns([1, 1.5])
    with col_thumb:
        if info.get("thumbnail"):
            st.image(info["thumbnail"], use_container_width=True)
    with col_details:
        st.subheader(info.get("title", "Video Seleccionado"))
        st.write(f"⏱️ **Duración:** `{fmt_time(info.get('duration'))}`")

    st.divider()
    
    col_tipo, col_formato, col_calidad = st.columns(3)
    
    with col_tipo:
        tipo_medio = st.radio("Tipo de Medio", ["Video", "Audio Solo"], horizontal=False)
    
    with col_formato:
        if tipo_medio == "Video":
            formato_ext = st.selectbox("Formato", ["MP4", "MKV", "WEBM", "MOV"])
        else:
            formato_ext = st.selectbox("Formato", ["MP3", "M4A", "WAV", "FLAC", "OPUS"])

    with col_calidad:
        if tipo_medio == "Video":
            res_sel = st.selectbox("Resolución", [2160, 1440, 1080, 720, 480, 360], format_func=lambda x: f"{x}p" + (" (4K)" if x==2160 else " (2K)" if x==1440 else ""))
        else:
            bitrate_sel = st.selectbox("Calidad Audio", [320, 256, 192, 128], format_func=lambda x: f"{x} kbps")

    st.markdown("### ✂️ Recorte de Tiempo (Opcional)")
    recortar = st.checkbox("Activar Recorte")
    
    if recortar:
        c1, c2 = st.columns(2)
        inicio_txt = c1.text_input("Tiempo Inicio", value="00:00")
        fin_txt = c2.text_input("Tiempo Fin", value=fmt_time(info.get("duration") or 0))

    st.write("")
    if st.button("🚀 Procesar y Descargar", type="primary"):
        tmp_dir = tempfile.mkdtemp()
        ext_lower = formato_ext.lower()
        
        try:
            opts = {
                "outtmpl": os.path.join(tmp_dir, "%(title)s.%(ext)s"),
                "quiet": True,
                "nocheckcertificate": True,
                "concurrent_fragment_downloads": 4,
                "extractor_args": {"youtube": {"player_client": ["android", "web"]}}
            }

            if tipo_medio == "Video":
                opts["format"] = f"bestvideo[height<={res_sel}]+bestaudio/best[height<={res_sel}]/best"
                opts["merge_output_format"] = ext_lower
            else:
                opts["format"] = "bestaudio/best"
                opts["postprocessors"] = [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": ext_lower,
                    "preferredquality": str(bitrate_sel),
                }]

            if recortar:
                seg_in = parse_time(inicio_txt)
                seg_out = parse_time(fin_txt)
                opts["download_ranges"] = download_range_func(None, [(seg_in, seg_out)])

            with st.spinner("⚡ Procesando archivo..."):
                with yt_dlp.YoutubeDL(opts) as ydl:
                    ydl.download([st.session_state["url"]])

            archivos = glob.glob(os.path.join(tmp_dir, "*.*"))
            if archivos:
                ruta = max(archivos, key=os.path.getmtime)
                with open(ruta, "rb") as f:
                    st.download_button(
                        label=f"💾 Guardar {formato_ext} en tu equipo", 
                        data=f.read(), 
                        file_name=os.path.basename(ruta),
                        mime=f"video/{ext_lower}" if tipo_medio=="Video" else f"audio/{ext_lower}"
                    )
                st.success("✅ ¡Archivo listo!")
            else:
                st.error("No se pudo generar el archivo.")

        except Exception as e:
            st.error(f"❌ Error durante el proceso: {e}")
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
