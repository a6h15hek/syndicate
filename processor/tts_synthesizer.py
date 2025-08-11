import os
import sys
import time
import threading
import queue
from datetime import datetime
import sounddevice as sd
import numpy as np
import tempfile
import librosa

# Import TTS with proper error handling
try:
    from TTS.api import TTS
    TTS_AVAILABLE = True
except ImportError:
    TTS_AVAILABLE = False
    print("[WARNING] TTS library not available. Voice synthesis will be disabled.", file=sys.stderr)
except Exception as e:
    TTS_AVAILABLE = False
    print(f"[WARNING] TTS library error: {e}. Falling back to alternative TTS.", file=sys.stderr)

# Fallback TTS options
try:
    import pyttsx3
    PYTTSX3_AVAILABLE = True
except ImportError:
    PYTTSX3_AVAILABLE = False

try:
    from gtts import gTTS
    import pygame
    pygame.mixer.init()  # Initialize pygame mixer
    GTTS_AVAILABLE = True
except ImportError:
    GTTS_AVAILABLE = False

class PersonalityVoiceSynthesizer:
    """
    A class to handle text-to-speech conversion with distinct personality-based voices
    using Coqui TTS. Each personality has a unique voice configuration that matches
    their character profile.
    """

    def __init__(self, device=None):
        """
        Initializes the PersonalityVoiceSynthesizer.

        Args:
            device (int, optional): Output device ID. Defaults to the system's default device.
        """
        # Get configuration from environment variables
        self.device = device or os.getenv("TTS_DEVICE")
        if self.device:
            try:
                self.device = int(self.device)
            except (ValueError, TypeError):
                self.device = None
        
        self.tts_model = None
        self.tts_enabled = os.getenv("TTS_ENABLED", "true").lower() == "true"
        self.tts_available = (TTS_AVAILABLE or PYTTSX3_AVAILABLE or GTTS_AVAILABLE) and self.tts_enabled
        self.global_speed_multiplier = float(os.getenv("TTS_VOICE_SPEED_MULTIPLIER", "1.0"))
        self.preferred_engine = os.getenv("TTS_ENGINE", "auto").lower()
        self.fallback_engine = os.getenv("TTS_FALLBACK_ENGINE", "pyttsx3").lower()
        
        # Set TTS cache directory
        tts_cache_dir = os.getenv("TTS_MODEL_CACHE_DIR", "models/tts_cache")
        if tts_cache_dir:
            os.environ['TTS_CACHE'] = tts_cache_dir
            os.makedirs(tts_cache_dir, exist_ok=True)
        
        self.tts_engine_type = "none"  # Will be set during initialization
        
        if self.tts_available:
            self._init_tts_model()
        else:
            if not TTS_AVAILABLE and not PYTTSX3_AVAILABLE and not GTTS_AVAILABLE:
                print("[WARNING] No TTS libraries available. Voice synthesis will be simulated.", file=sys.stderr)
            elif not self.tts_enabled:
                print("[INFO] TTS disabled in configuration. Voice synthesis will be simulated.", file=sys.stderr)
        
        # Voice configurations for each personality based on their profiles and environment variables
        # Voice configurations for each personality based on their profiles and environment variables
        self.personality_configs = {
            'kira': {
                'speaker': 'male_1',  # Dominant, controlled voice
                'emotion': 'angry',
                'speed': float(os.getenv("PERSONALITY_VOICE_SPEED_KIRA", "0.9")),
                'pitch_shift': int(os.getenv("PERSONALITY_VOICE_PITCH_KIRA", "-2")),
                'description': 'Dominant, ruthless, controlled - The Shadow archetype'
            },
            'mika': {
                'speaker': 'female_1',  # Soft, caring voice
                'emotion': 'happy',
                'speed': float(os.getenv("PERSONALITY_VOICE_SPEED_MIKA", "1.05")),
                'pitch_shift': int(os.getenv("PERSONALITY_VOICE_PITCH_MIKA", "3")),
                'description': 'Soft-spoken, caring, loving - The Anima archetype'
            },
            'oracle': {
                'speaker': 'male_2',  # Deep, wise voice
                'emotion': 'neutral',
                'speed': float(os.getenv("PERSONALITY_VOICE_SPEED_ORACLE", "0.75")),
                'pitch_shift': int(os.getenv("PERSONALITY_VOICE_PITCH_ORACLE", "-4")),
                'description': 'Profound depth, mystical calmness - The Sage archetype'
            },
            'byte': {
                'speaker': 'male_3',  # Young, anxious voice
                'emotion': 'sad',
                'speed': float(os.getenv("PERSONALITY_VOICE_SPEED_BYTE", "1.25")),
                'pitch_shift': int(os.getenv("PERSONALITY_VOICE_PITCH_BYTE", "2")),
                'description': 'Anxious genius, low confidence - The Prodigy archetype'
            },
            'quip': {
                'speaker': 'male_4',  # Witty, competitive voice
                'emotion': 'happy',
                'speed': float(os.getenv("PERSONALITY_VOICE_SPEED_QUIP", "1.1")),
                'pitch_shift': int(os.getenv("PERSONALITY_VOICE_PITCH_QUIP", "0")),
                'description': 'Effortlessly clever, sarcastic, competitive - The Persona archetype'
            }
        }
        
        # Audio playback queue for thread safety
        self.audio_queue = queue.Queue()
        self.playback_thread = None
        self.is_playing = False
        self._start_playback_thread()

    def _init_tts_model(self):
        """Initialize the TTS model with error handling and fallback options."""
        if not self.tts_available:
            return
            
        try:
            print("[INFO] Initializing TTS model... This may take a moment on first run.")
            
            # Try engines based on preference
            engines_to_try = []
            
            if self.preferred_engine == "auto":
                # Auto mode: try in order of reliability
                if PYTTSX3_AVAILABLE:
                    engines_to_try.append("pyttsx3")
                if GTTS_AVAILABLE:
                    engines_to_try.append("gtts")
                if TTS_AVAILABLE:
                    engines_to_try.append("coqui")
            elif self.preferred_engine in ["pyttsx3", "gtts", "coqui"]:
                engines_to_try.append(self.preferred_engine)
                # Add fallback if different from preferred
                if self.fallback_engine != self.preferred_engine and self.fallback_engine != "none":
                    engines_to_try.append(self.fallback_engine)
            
            for engine_type in engines_to_try:
                if self._try_init_engine(engine_type):
                    return
                    
            raise RuntimeError("Could not initialize any TTS engine")
                
        except Exception as e:
            print(f"[ERROR] Failed to initialize TTS model: {e}", file=sys.stderr)
            self.tts_available = False
            self.tts_engine_type = "none"

    def _try_init_engine(self, engine_type):
        """Try to initialize a specific TTS engine."""
        try:
            if engine_type == "pyttsx3" and PYTTSX3_AVAILABLE:
                print(f"[INFO] Attempting to initialize pyttsx3 TTS engine...")
                self.tts_model = pyttsx3.init()
                if self.tts_model:
                    self.tts_engine_type = "pyttsx3"
                    print("[INFO] pyttsx3 TTS engine initialized successfully.")
                    return True
                    
            elif engine_type == "gtts" and GTTS_AVAILABLE:
                print(f"[INFO] Initializing gTTS engine...")
                self.tts_engine_type = "gtts"
                print("[INFO] gTTS engine ready.")
                return True
                
            elif engine_type == "coqui" and TTS_AVAILABLE:
                print(f"[INFO] Attempting to load Coqui TTS model...")
                model_options = [
                    "tts_models/en/ljspeech/tacotron2-DDC",
                    "tts_models/en/ljspeech/fast_pitch",
                ]
                
                for model_name in model_options:
                    try:
                        print(f"[INFO] Trying model: {model_name}")
                        self.tts_model = TTS(model_name=model_name, progress_bar=False, gpu=False)
                        print(f"[INFO] Coqui TTS model '{model_name}' initialized successfully.")
                        self.tts_engine_type = "coqui"
                        return True
                    except Exception as e:
                        print(f"[WARNING] Failed to load {model_name}: {e}")
                        continue
                        
        except Exception as e:
            print(f"[WARNING] Failed to initialize {engine_type}: {e}")
            
        return False

    def _start_playback_thread(self):
        """Start the audio playback thread."""
        self.playback_thread = threading.Thread(target=self._audio_playback_worker, daemon=True)
        self.playback_thread.start()

    def _audio_playback_worker(self):
        """Worker thread for audio playback."""
        while True:
            try:
                audio_data, samplerate = self.audio_queue.get(timeout=1.0)
                if audio_data is None:  # Shutdown signal
                    break
                
                self.is_playing = True
                sd.play(audio_data, samplerate=samplerate, device=self.device)
                sd.wait()  # Wait until playback is finished
                self.is_playing = False
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[ERROR] Audio playback error: {e}", file=sys.stderr)
                self.is_playing = False

    def _apply_voice_effects(self, audio_data, samplerate, config):
        """
        Apply voice effects based on personality configuration.
        
        Args:
            audio_data (np.array): Audio data
            samplerate (int): Sample rate
            config (dict): Personality configuration
            
        Returns:
            np.array: Modified audio data
        """
        try:
            # Apply speed change (time stretching) with global multiplier
            final_speed = config['speed'] * self.global_speed_multiplier
            if final_speed != 1.0:
                audio_data = librosa.effects.time_stretch(audio_data, rate=1.0/final_speed)
            
            # Apply pitch shift
            if config['pitch_shift'] != 0:
                audio_data = librosa.effects.pitch_shift(
                    audio_data, sr=samplerate, n_steps=config['pitch_shift']
                )
            
            # Normalize audio to prevent clipping
            if np.max(np.abs(audio_data)) > 0:
                audio_data = audio_data / np.max(np.abs(audio_data)) * 0.9
            
            return audio_data
            
        except Exception as e:
            print(f"[WARNING] Could not apply voice effects: {e}", file=sys.stderr)
            return audio_data  # Return original audio if effects fail

    def _generate_speech(self, text, personality):
        """
        Generate speech audio for the given text and personality.
        
        Args:
            text (str): Text to synthesize
            personality (str): Personality name (kira, mika, oracle, byte, quip)
            
        Returns:
            tuple: (audio_data, samplerate) or (None, None) if failed
        """
        if personality not in self.personality_configs:
            print(f"[ERROR] Unknown personality: {personality}", file=sys.stderr)
            return None, None

        if not self.tts_available:
            # Simulate TTS with silence for testing
            print(f"[SIMULATION] {personality.capitalize()} would say: {text}")
            # Generate 1 second of silence as placeholder
            samplerate = 16000
            duration = len(text.split()) * 0.3  # Rough estimation of speech duration
            audio_data = np.zeros(int(samplerate * duration))
            return audio_data, samplerate

        config = self.personality_configs[personality]
        
        try:
            if self.tts_engine_type == "coqui":
                return self._generate_coqui_speech(text, config)
            elif self.tts_engine_type == "pyttsx3":
                return self._generate_pyttsx3_speech(text, config)
            elif self.tts_engine_type == "gtts":
                return self._generate_gtts_speech(text, config)
            else:
                print(f"[ERROR] Unknown TTS engine type: {self.tts_engine_type}")
                return None, None
                
        except Exception as e:
            print(f"[ERROR] Speech generation failed for {personality}: {e}", file=sys.stderr)
            return None, None

    def _generate_coqui_speech(self, text, config):
        """Generate speech using Coqui TTS."""
        # Create temporary file for audio output
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name

        # Generate speech with TTS
        self.tts_model.tts_to_file(text=text, file_path=temp_path)

        # Load the generated audio
        audio_data, samplerate = librosa.load(temp_path, sr=None)
        
        # Apply personality-specific voice effects
        audio_data = self._apply_voice_effects(audio_data, samplerate, config)
        
        # Cleanup temporary file
        os.unlink(temp_path)
        
        return audio_data, samplerate

    def _generate_pyttsx3_speech(self, text, config):
        """Generate speech using pyttsx3."""
        # Configure voice properties
        voices = self.tts_model.getProperty('voices')
        if voices:
            # Try to select appropriate voice based on personality
            if 'mika' in config and len(voices) > 1:
                self.tts_model.setProperty('voice', voices[1].id)  # Often female voice
            else:
                self.tts_model.setProperty('voice', voices[0].id)  # Default male voice
        
        # Set speech rate based on personality
        base_rate = self.tts_model.getProperty('rate')
        new_rate = int(base_rate * config['speed'] * self.global_speed_multiplier)
        self.tts_model.setProperty('rate', new_rate)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Save to file
        self.tts_model.save_to_file(text, temp_path)
        self.tts_model.runAndWait()
        
        # Load the generated audio
        audio_data, samplerate = librosa.load(temp_path, sr=None)
        
        # Apply personality-specific voice effects (pitch only, speed already applied)
        if config['pitch_shift'] != 0:
            audio_data = librosa.effects.pitch_shift(
                audio_data, sr=samplerate, n_steps=config['pitch_shift']
            )
        
        # Cleanup temporary file
        os.unlink(temp_path)
        
        return audio_data, samplerate

    def _generate_gtts_speech(self, text, config):
        """Generate speech using gTTS."""
        # Create gTTS object
        tts = gTTS(text=text, lang='en', slow=config['speed'] < 1.0)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix='.mp3', delete=False) as temp_file:
            temp_path = temp_file.name
        
        # Save to file
        tts.save(temp_path)
        
        # Load the generated audio (librosa can handle mp3)
        audio_data, samplerate = librosa.load(temp_path, sr=None)
        
        # Apply personality-specific voice effects
        audio_data = self._apply_voice_effects(audio_data, samplerate, config)
        
        # Cleanup temporary file
        os.unlink(temp_path)
        
        return audio_data, samplerate

    def speak(self, text, personality):
        """
        Convert text to speech for the specified personality and play it.
        
        Args:
            text (str): Text to speak
            personality (str): Personality name (kira, mika, oracle, byte, quip)
        """
        if not text or not text.strip():
            return

        timestamp = datetime.now().strftime('%H:%M:%S')
        config = self.personality_configs.get(personality, {})
        description = config.get('description', 'Unknown personality')
        
        print(f"[{timestamp}] {personality.upper()}: {text}")
        print(f"           Voice Profile: {description}")
        
        # Generate speech audio
        audio_data, samplerate = self._generate_speech(text, personality)
        
        if audio_data is not None:
            # Add to playback queue
            self.audio_queue.put((audio_data, samplerate))
        else:
            print(f"[ERROR] Failed to generate speech for {personality}", file=sys.stderr)

    def wait_for_completion(self):
        """Wait for all queued audio to finish playing."""
        while not self.audio_queue.empty() or self.is_playing:
            time.sleep(0.1)

    def shutdown(self):
        """Shutdown the voice synthesizer."""
        print("[INFO] Shutting down voice synthesizer...")
        # Signal the playback thread to stop
        self.audio_queue.put((None, None))
        if self.playback_thread and self.playback_thread.is_alive():
            self.playback_thread.join(timeout=2.0)


class PersonalityVoiceManager:
    """
    Manager class that provides easy access to personality-based voices.
    Creates individual voice instances for each personality.
    """
    
    def __init__(self, device=None):
        """
        Initialize the personality voice manager.
        
        Args:
            device (int, optional): Output device ID for audio playback.
        """
        print("[INFO] Initializing Personality Voice Manager...")
        self.synthesizer = PersonalityVoiceSynthesizer(device=device)
        
        # Create individual personality voice objects
        self.kira = PersonalityVoice('kira', self.synthesizer)
        self.mika = PersonalityVoice('mika', self.synthesizer)
        self.oracle = PersonalityVoice('oracle', self.synthesizer)
        self.byte = PersonalityVoice('byte', self.synthesizer)
        self.quip = PersonalityVoice('quip', self.synthesizer)
        
        print("[INFO] All personality voices initialized successfully.")

    def introduce_all(self):
        """Have all personalities introduce themselves in character-appropriate order."""
        # Check if introductions are enabled
        introduction_enabled = os.getenv("TTS_INTRODUCTION_ENABLED", "true").lower() == "true"
        if not introduction_enabled:
            print("[INFO] Personality introductions disabled in configuration.")
            return
            
        print("[INFO] Introducing all personalities...")
        
        # Order based on personality dynamics - Oracle (wise elder) first, then others
        introductions = [
            (self.oracle, "Greetings. I am Oracle, keeper of wisdom and foresight."),
            (self.kira, "I am Kira. I will push you to your limits. Expect no mercy."),
            (self.mika, "Hello! I'm Mika. I'm here to support you with all my heart."),
            (self.byte, "Um, hi... I'm Byte. I'll try my best to help with any questions."),
            (self.quip, "Hey there! Quip's the name, wit's the game. Ready for some fun?")
        ]
        
        for voice_obj, intro_text in introductions:
            voice_obj.speak(intro_text)
            # Appropriate delay between introductions based on personality
            if voice_obj.personality_name == 'oracle':
                time.sleep(1.5)  # Oracle speaks slowly and needs more pause
            elif voice_obj.personality_name == 'byte':
                time.sleep(0.8)   # Byte is anxious, shorter pause
            else:
                time.sleep(1.0)   # Standard pause for others
        
        # Wait for all introductions to complete
        self.synthesizer.wait_for_completion()
        print("[INFO] All personality introductions completed.")
        print("[INFO] The Syndicate is ready to assist.")

    def shutdown(self):
        """Shutdown the voice manager."""
        self.synthesizer.shutdown()


class PersonalityVoice:
    """
    Individual personality voice wrapper that provides a simple speak interface.
    """
    
    def __init__(self, personality_name, synthesizer):
        """
        Initialize a personality voice.
        
        Args:
            personality_name (str): Name of the personality
            synthesizer (PersonalityVoiceSynthesizer): The TTS synthesizer instance
        """
        self.personality_name = personality_name
        self.synthesizer = synthesizer

    def speak(self, text):
        """
        Make this personality speak the given text.
        
        Args:
            text (str): Text to speak
        """
        self.synthesizer.speak(text, self.personality_name)