# text_to_speech.py
import logging
import random
import sounddevice as sd
from TTS.api import TTS
import shutil
import config

class TextToSpeech:
    """Handles text-to-speech conversion using Coqui TTS."""
    def __init__(self):
        logging.info("Initializing TextToSpeech...")
        self._check_dependencies()
        self.tts_instances = {} # Cache for loaded models
        self.voices = config.TTS_VOICES

    def _check_dependencies(self):
        """Checks for required system dependencies like espeak-ng."""
        if not shutil.which("espeak-ng") and not shutil.which("espeak"):
            logging.warning("="*80)
            logging.warning("`espeak-ng` or `espeak` not found in your system's PATH.")
            logging.warning("This is required by some TTS models for phonemization.")
            logging.warning("Please install it to ensure all voices work correctly.")
            logging.warning("  - On Debian/Ubuntu: sudo apt-get install espeak-ng")
            logging.warning("  - On macOS (Homebrew): brew install espeak-ng")
            logging.warning("  - On Windows: Download from https://github.com/espeak-ng/espeak-ng/releases")
            logging.warning("="*80)

    def speak(self, text, personality=None):
        """Converts text to speech using a specified or random voice and plays it."""
        try:
            # Select voice configuration
            if personality and personality in self.voices:
                voice_config = self.voices[personality]
                logging.info(f"Using specified personality: {personality}")
            else:
                if personality:
                    logging.warning(f"Personality '{personality}' not found. Selecting a random voice.")
                # Randomly select a personality name
                personality = random.choice(list(self.voices.keys()))
                voice_config = self.voices[personality]
                logging.info(f"Using random personality: {personality}")

            model_name = voice_config["model_name"]
            speaker = voice_config["speaker"]

            # Load model if not already cached
            if model_name not in self.tts_instances:
                logging.info(f"Loading TTS model: {model_name}...")
                self.tts_instances[model_name] = TTS(model_name=model_name, gpu=config.TTS_USE_GPU)
                logging.info(f"Model {model_name} loaded.")

            tts_model = self.tts_instances[model_name]

            logging.info(f"Generating speech for: '{text}' with personality '{personality}' (Model: {model_name}, Speaker: {speaker or 'default'})")

            wav = tts_model.tts(text=text, speaker=speaker)

            # Play the audio
            sd.play(
                wav,
                samplerate=tts_model.synthesizer.output_sample_rate,
                device=config.AUDIO_OUTPUT_DEVICE
            )
            sd.wait()
            logging.info("Speech playback finished.")
        except Exception as e:
            logging.error(f"Failed to generate or play speech: {e}")