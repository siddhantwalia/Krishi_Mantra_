import requests
import os
from dotenv import load_dotenv
from groq import Groq
from pathlib import Path

load_dotenv()
def text_to_speech(text: str) -> bytes | None:
    """Generates speech using Groq and returns WAV audio bytes."""
    client = Groq()

    try:
        response = client.audio.speech.create(
            model="playai-tts",
            voice="Aaliyah-PlayAI",
            response_format="wav",
            input=text,
        )

        # ✅ Groq returns full audio bytes directly
        audio_bytes = response.read()

        # Optional: save to file
        speech_file_path = "speech.wav"
        with open(speech_file_path, "wb") as f:
            f.write(audio_bytes)

        return audio_bytes

    except Exception as e:
        print("TTS Error:", e)
        return None

# audio = text_to_speech("aapka naam kya hai")

# if audio:
#     output_path = "farmer_response.mp3"
#     with open(output_path, "wb") as f:
#         f.write(audio)
#     print("✅ Speech saved to:", output_path)