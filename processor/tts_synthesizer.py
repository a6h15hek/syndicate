import os
import sys
import time
import threading
import queue
import logging
from datetime import datetime
import sounddevice as sd
import numpy as np
import tempfile
import librosa

# --- Setup Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - (%(threadName)-10s) - %(message)s',
)
log = logging.getLogger(__name__)


# --- Import TTS with proper error handling ---
try:
    from TTS.api import TTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    log.warning("Coqui TTS library not available. Voice synthesis will be disabled.")
except Exception as e:
    TTS_AVAILABLE = False
    log.warning(f"Coqui TTS library error: {e}. Falling back to alternative TTS.")

# --- Fallback TTS options ---
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

class PersonalityVoiceSynthesizer:
    """
    Handles text-to-speech conversion using a multi-speaker TTS model.
    Each personality is mapped to a specific speaker, with unique voice characteristics
    defined in the environment configuration.
    """

    def __init__(self, device=None):
        """
        Initializes the PersonalityVoiceSynthesizer.

        Args:
            device (int, optional): Output device ID. Defaults to the system's default device.
        """
        log.info("Initializing PersonalityVoiceSynthesizer...")

        # --- Audio Device Configuration ---
        raw_device = device or os.getenv("TTS_DEVICE")
        self.device = int(raw_device) if raw_device and raw_device.isdigit() else None
        self._log_audio_device_info()

        # --- General TTS Configuration ---
        self.tts_enabled = os.getenv("TTS_ENABLED", "true").lower() == "true"
        self.use_gpu = os.getenv("TTS_GPU_ACCELERATION", "false").lower() == "true"
        self.global_speed_multiplier = float(os.getenv("TTS_VOICE_SPEED_MULTIPLIER", "1.0"))
        
        # --- Model and Engine Configuration ---
        self.tts_model_name = os.getenv("TTS_MODEL", "tts_models/en/vctk/vits")
        self.preferred_engine = os.getenv("TTS_ENGINE", "coqui").lower()
        self.fallback_engine = os.getenv("TTS_FALLBACK_ENGINE", "pyttsx3").lower()
        
        # Set TTS cache directory
        tts_cache_dir = os.getenv("TTS_MODEL_CACHE_DIR", "models/tts_cache")
        os.environ['TTS_HOME'] = tts_cache_dir
        os.makedirs(tts_cache_dir, exist_ok=True)
        
        self.tts_model = None
        self.tts_engine_type = "none"
        
        if self.tts_enabled:
            self._init_tts_engine()
        else:
            log.info("TTS is disabled in the configuration. Voice synthesis will be simulated.")

        # --- Personality Voice Customization ---
        self.personality_configs = self._load_personality_configs()

        # --- Audio Playback Queue ---
        self.audio_queue = queue.Queue()
        self.playback_thread = None
        self.is_playing = threading.Event()
        self._start_playback_thread()
        log.info("PersonalityVoiceSynthesizer initialized.")

    def _load_personality_configs(self):
        """Loads voice configurations for all personalities from environment variables."""
        personalities = ['kira', 'mika', 'oracle', 'byte', 'quip']
        configs = {}
        for p in personalities:
            p_upper = p.upper()
            configs[p] = {
                'speaker': os.getenv(f"PERSONALITY_SPEAKER_{p_upper}"),
                'speed': float(os.getenv(f"PERSONALITY_VOICE_SPEED_{p_upper}", "1.0")),
                'pitch': int(os.getenv(f"PERSONALITY_VOICE_PITCH_{p_upper}", "0")),
                'description': f'{p.capitalize()} personality voice'
            }
            if not configs[p]['speaker']:
                log.warning(f"Speaker for personality '{p}' is not defined in .env. Coqui TTS may fail.")
        return configs

    def _log_audio_device_info(self):
        """Logs information about the audio devices and configuration."""
        log.info("--- TTS Audio Settings ---")
        log.info(f"Configured Audio Device (TTS_DEVICE): {os.getenv('TTS_DEVICE', 'System Default')}")
        log.info(f"Using Audio Device ID: {'System Default' if self.device is None else self.device}")
        try:
            devices = sd.query_devices()
            log.info("Available Audio Output Devices:")
            found_device = False
            for i, device in enumerate(devices):
                if device['max_output_channels'] > 0:
                    is_default = (i == sd.default.device[1])
                    default_str = " (Default)" if is_default else ""
                    log.info(f"  ID {i}: {device['name']}{default_str}")
                    found_device = True
            if not found_device:
                log.warning("No audio output devices found.")
        except Exception as e:
            log.error(f"Could not list audio devices: {e}")
        log.info("--- End of Audio Settings ---")

    def _init_tts_engine(self):
        """Initializes the TTS engine based on configuration."""
        log.info(f"Preferred TTS engine: {self.preferred_engine}")
        
        # Attempt to initialize preferred engine
        if self.preferred_engine == 'coqui' and TTS_AVAILABLE:
            if self._try_init_coqui():
                return

        if self.preferred_engine == 'pyttsx3' and PYTTSX3_AVAILABLE:
            if self._try_init_pyttsx3():
                return

        # Attempt to initialize fallback engine
        log.warning(f"Preferred engine '{self.preferred_engine}' failed. Trying fallback.")
        if self.fallback_engine == 'pyttsx3' and PYTTSX3_AVAILABLE:
            if self._try_init_pyttsx3():
                return
        
        log.error("Could not initialize any TTS engine. Voice synthesis will be simulated.")
        self.tts_engine_type = "none"

    def _try_init_coqui(self):
        """Tries to initialize the Coqui TTS engine."""
        try:
            log.info(f"Attempting to load Coqui TTS model: {self.tts_model_name}")
            self.tts_model = TTS(model_name=self.tts_model_name, progress_bar=False, gpu=self.use_gpu)
            self.tts_engine_type = "coqui"
            log.info(f"Coqui TTS model '{self.tts_model_name}' initialized successfully.")
            return True
        except Exception as e:
            log.error(f"Failed to load Coqui TTS model '{self.tts_model_name}': {e}")
            return False

    def _try_init_pyttsx3(self):
        """Tries to initialize the pyttsx3 engine."""
        try:
            log.info("Attempting to initialize pyttsx3 TTS engine...")
            self.tts_model = pyttsx3.init()
            if self.tts_model:
                self.tts_engine_type = "pyttsx3"
                log.info("pyttsx3 TTS engine initialized successfully.")
                return True
            return False
        except Exception as e:
            log.error(f"Failed to initialize pyttsx3: {e}")
            return False

    def _start_playback_thread(self):
        """Starts the dedicated audio playback thread."""
        self.playback_thread = threading.Thread(target=self._audio_playback_worker, name="TTSPlaybackThread", daemon=True)
        self.playback_thread.start()

    def _audio_playback_worker(self):
        """
        Worker thread that pulls audio data from the queue and plays it.
        This ensures that speech requests are handled sequentially.
        """
        while True:
            try:
                text, personality, audio_data, samplerate = self.audio_queue.get()
                if audio_data is None:  # Shutdown signal
                    log.info("Playback thread received shutdown signal.")
                    break
                
                self.is_playing.set()
                log.info(f"Starting playback for {personality.upper()}: '{text}'")
                sd.play(audio_data, samplerate=samplerate, device=self.device)
                sd.wait()  # Block until playback is finished
                log.info(f"Playback completed for {personality.upper()}.")
                self.is_playing.clear()
                self.audio_queue.task_done()

            except queue.Empty:
                continue
            except Exception as e:
                log.error(f"Audio playback error: {e}", exc_info=True)
                self.is_playing.clear()


    def _apply_pitch_shift(self, audio_data, samplerate, pitch_steps):
        """Applies pitch shifting to the audio data."""
        if pitch_steps == 0:
            return audio_data
        try:
            log.debug(f"Applying pitch shift of {pitch_steps} steps.")
            return librosa.effects.pitch_shift(audio_data, sr=samplerate, n_steps=pitch_steps)
        except Exception as e:
            log.warning(f"Could not apply pitch shift: {e}")
            return audio_data

    def _generate_speech(self, text, personality):
        """
        Generates speech audio for the given text and personality.
        This method dispatches to the appropriate engine-specific function.
        """
        if not self.tts_enabled or self.tts_engine_type == "none":
            log.info(f"[SIMULATED] {personality.upper()}: {text}")
            duration = len(text.split()) * 0.3  # Rough estimate
            return np.zeros(int(16000 * duration)), 16000

        config = self.personality_configs[personality]
        
        try:
            if self.tts_engine_type == "coqui":
                return self._generate_coqui_speech(text, config)
            elif self.tts_engine_type == "pyttsx3":
                return self._generate_pyttsx3_speech(text, config)
            else:
                raise RuntimeError(f"Unknown TTS engine type: {self.tts_engine_type}")
                
        except Exception as e:
            log.error(f"Speech generation failed for {personality}: {e}", exc_info=True)
            return None, None

    def _generate_coqui_speech(self, text, config):
        """Generates speech using the Coqui TTS engine."""
        final_speed = config['speed'] * self.global_speed_multiplier
        
        # Coqui TTS expects a numpy array, not a file path for processing
        wav = self.tts_model.tts(text=text, speaker=config['speaker'], speed=final_speed)
        audio_data = np.array(wav, dtype=np.float32)
        samplerate = self.tts_model.synthesizer.output_sample_rate

        # Apply pitch shift post-synthesis
        audio_data = self._apply_pitch_shift(audio_data, samplerate, config['pitch'])
        
        # Normalize audio to prevent clipping
        if np.max(np.abs(audio_data)) > 0:
            audio_data = audio_data / np.max(np.abs(audio_data)) * 0.98
            
        return audio_data, samplerate

    def _generate_pyttsx3_speech(self, text, config):
        """Generates speech using the pyttsx3 fallback engine."""
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name

        self.tts_model.save_to_file(text, temp_path)
        self.tts_model.runAndWait()

        if not os.path.exists(temp_path) or os.path.getsize(temp_path) == 0:
            log.error(f"pyttsx3 generated an empty file for: {text}")
            return None, None

        audio_data, samplerate = librosa.load(temp_path, sr=None)
        os.unlink(temp_path)
        
        # pyttsx3 doesn't support speed/pitch natively, so we apply them here
        final_speed = config['speed'] * self.global_speed_multiplier
        if final_speed != 1.0:
            audio_data = librosa.effects.time_stretch(audio_data, rate=1.0/final_speed)
        
        audio_data = self._apply_pitch_shift(audio_data, samplerate, config['pitch'])
        
        return audio_data, samplerate

    def speak(self, text, personality):
        """
        Queues a text-to-speech request. The actual synthesis and playback
        happen in background threads to avoid blocking.
        """
        if not text or not text.strip():
            return
        if personality not in self.personality_configs:
            log.error(f"Unknown personality: {personality}")
            return

        log.info(f"Received speech request for {personality.upper()}. Synthesizing...")
        
        # Generate speech audio
        audio_data, samplerate = self._generate_speech(text, personality)
        
        if audio_data is not None and audio_data.size > 0:
            log.debug(f"Speech for '{text}' synthesized successfully. Adding to playback queue.")
            # The queue item now includes text and personality for better logging
            self.audio_queue.put((text, personality, audio_data, samplerate))
        else:
            log.warning(f"Generated audio for {personality.upper()} is empty. Skipping playback.")

    def wait_for_completion(self):
        """
        Blocks until all queued audio has finished playing.
        This is crucial for sequential dialogues.
        """
        log.debug("Waiting for audio queue to complete...")
        self.audio_queue.join()
        if self.is_playing.is_set():
            self.is_playing.wait(timeout=5.0) # Wait for the last item to finish playing
        log.debug("Audio queue completed.")

    def shutdown(self):
        """Shuts down the voice synthesizer and its threads."""
        log.info("Shutting down PersonalityVoiceSynthesizer...")
        self.wait_for_completion()
        self.audio_queue.put((None, None, None, None))  # Shutdown signal for playback thread
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=2.0)
        log.info("Shutdown complete.")
