# config.py

# --- Speech-to-Text (STT) Settings ---
STT_MODEL_SIZE = "base.en"  # Options: "tiny.en", "base.en", "small.en", "medium.en"
# For GPU: STT_DEVICE, STT_COMPUTE_TYPE = "cuda", "float16"
# For CPU:
STT_DEVICE, STT_COMPUTE_TYPE = "cpu", "int8"


# --- Audio Settings ---
AUDIO_SAMPLE_RATE = 16000 # Sample rate for audio recording
AUDIO_BLOCK_DURATION_SECONDS = 2 # Process audio in 2-second chunks
AUDIO_SILENCE_THRESHOLD = 350 # Audio level below which is considered silence
AUDIO_SILENCE_DURATION_SECONDS = 2 # How many seconds of silence indicates the end of speech


# --- Text-to-Speech (TTS) Settings ---
# A mapping of personality names to their voice models.
# Voice models are from Coqui TTS: https://github.com/coqui-ai/TTS/blob/dev/TTS/server/configs/config.json
TTS_VOICES = {
    # Mika: The Anima. Soft-spoken, caring, and deeply empathetic.
    # Voice: An expressive and warm female voice to convey genuine emotion and care.
    "Mika": {
        "model_name": "tts_models/en/jenny/jenny", "speaker": None
    },

    # Kira: The Shadow. Dominant, ruthless, and controlled.
    # Voice: A deeper, authoritative male voice that sounds commanding and pragmatic.
    "Kira": {
        "model_name": "tts_models/en/vctk/vits", "speaker": "p227"
    },

    # Quip: The Persona. Effortlessly clever, sarcastic, and competitive.
    # Voice: A standard, clear male voice suitable for delivering witty and sharp remarks.
    "Quip": {
        "model_name": "tts_models/en/vctk/vits", "speaker": "p225"
    },

    # Oracle: The Sage. Profound, calm, and wise.
    # Voice: A mature, deeper male voice that speaks with measured calmness and foresight.
    "Oracle": {
        "model_name": "tts_models/en/vctk/vits", "speaker": "p236"
    },

    # Byte: The Logos. Anxious genius, high intellect but low confidence.
    # Voice: A younger-sounding male voice to reflect his age (17) and prodigy status.
    "Byte": {
        "model_name": "tts_models/en/vctk/vits", "speaker": "p361"
    },
}
# For GPU: TTS_USE_GPU = True
# For CPU:
TTS_USE_GPU = False