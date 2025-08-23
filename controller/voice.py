import os
import sys
from datetime import datetime
from processor.tts_synthesizer import PersonalityVoiceManager

# --- Configuration ---
# All configuration and environment variable loading is handled in main.py
LOG_FILE = "logs/voice_log.txt"

# --- Advanced Voice Settings from .env ---
TTS_ENABLED = os.getenv("TTS_ENABLED", "true").lower() == "true"
TTS_DEVICE = os.getenv("TTS_DEVICE")
TTS_INTRODUCTION_ENABLED = os.getenv("TTS_INTRODUCTION_ENABLED", "true").lower() == "true"

class VoiceSystemManager:
    """
    Manager class for the voice system that handles initialization,
    logging, and provides a clean interface to the personality voices.
    """
    
    def __init__(self):
        """Initialize the voice system manager."""
        self.voice_manager = None
        self.log_file = LOG_FILE
        self._init_logging()
        
        if TTS_ENABLED:
            try:
                self._init_voice_system()
            except Exception as e:
                self._log_error(f"Failed to initialize voice system: {e}")
                print(f"[ERROR] Voice system initialization failed: {e}", file=sys.stderr)
                self.voice_manager = None
        else:
            self._log_info("TTS disabled in configuration")
            print("[INFO] TTS disabled in configuration.")

    def _init_logging(self):
        """Initialize logging for voice system."""
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        self._log_info("Voice system logging initialized")

    def _init_voice_system(self):
        """Initialize the personality voice system."""
        device_id = None
        if TTS_DEVICE:
            try:
                device_id = int(TTS_DEVICE)
                print(f"[INFO] Using configured TTS_DEVICE: {device_id}")
            except (ValueError, TypeError):
                self._log_warning(f"Invalid TTS_DEVICE value: {TTS_DEVICE}, using default")
                print(f"[WARNING] Invalid TTS_DEVICE value: '{TTS_DEVICE}'. Using default audio device.")
        
        self.voice_manager = PersonalityVoiceManager(device=device_id)
        self._log_info("Personality voice system initialized successfully")

    def _log_message(self, level, message):
        """Log a message with timestamp."""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_entry = f"[{timestamp}] [{level}] {message}"
        
        try:
            with open(self.log_file, "a") as log_file:
                log_file.write(log_entry + "\n")
        except Exception as e:
            print(f"[ERROR] Failed to write to log: {e}", file=sys.stderr)

    def _log_info(self, message):
        """Log an info message."""
        self._log_message("INFO", message)

    def _log_warning(self, message):
        """Log a warning message."""
        self._log_message("WARNING", message)

    def _log_error(self, message):
        """Log an error message."""
        self._log_message("ERROR", message)

    def introduce_personalities(self):
        """Have all personalities introduce themselves."""
        if not self.voice_manager:
            self._log_warning("Voice system not available for introductions")
            print("[WARNING] Voice system not available for introductions.")
            return False

        if not TTS_INTRODUCTION_ENABLED:
            self._log_info("Personality introductions disabled in configuration")
            print("[INFO] Personality introductions disabled in configuration.")
            return True

        try:
            self._log_info("Starting personality introductions")
            self.voice_manager.introduce_all()
            self._log_info("Personality introductions completed successfully")
            return True
        except Exception as e:
            self._log_error(f"Failed during personality introductions: {e}")
            print(f"[ERROR] Failed during personality introductions: {e}", file=sys.stderr)
            return False

    def get_personality_voices(self):
        """
        Get individual personality voice objects for direct access.
        
        Returns:
            dict: Dictionary containing personality voice objects, or None if not available
        """
        if not self.voice_manager:
            return None
            
        return {
            'kira': self.voice_manager.kira,
            'mika': self.voice_manager.mika,
            'oracle': self.voice_manager.oracle,
            'byte': self.voice_manager.byte,
            'quip': self.voice_manager.quip
        }

    def is_voice_system_available(self):
        """Check if the voice system is available and ready."""
        return self.voice_manager is not None

    def speak_as_personality(self, personality_name, text):
        """
        Make a specific personality speak the given text.
        
        Args:
            personality_name (str): Name of the personality (kira, mika, oracle, byte, quip)
            text (str): Text to speak
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.voice_manager:
            self._log_warning(f"Voice system not available for {personality_name}")
            return False

        try:
            personality_voices = self.get_personality_voices()
            if personality_name.lower() in personality_voices:
                personality_voice = personality_voices[personality_name.lower()]
                personality_voice.speak(text)
                self._log_info(f"{personality_name} spoke: {text}")
                return True
            else:
                self._log_error(f"Unknown personality: {personality_name}")
                return False
        except Exception as e:
            self._log_error(f"Failed to make {personality_name} speak: {e}")
            return False

    def wait_for_completion(self):
        """Wait for all queued speech to complete."""
        if self.voice_manager:
            try:
                self.voice_manager.synthesizer.wait_for_completion()
            except Exception as e:
                self._log_error(f"Error waiting for speech completion: {e}")

    def shutdown(self):
        """Shutdown the voice system."""
        if self.voice_manager:
            try:
                self._log_info("Shutting down voice system")
                self.voice_manager.shutdown()
                self._log_info("Voice system shutdown complete")
                print("[INFO] Voice system shutdown complete.")
            except Exception as e:
                self._log_error(f"Error during voice system shutdown: {e}")
                print(f"[WARNING] Error during voice system shutdown: {e}", file=sys.stderr)
        else:
            self._log_info("Voice system was not initialized, nothing to shutdown")


def initialize_voice_system():
    """
    Initialize and return the voice system manager.
    This function provides the main entry point for the voice system.
    
    Returns:
        VoiceSystemManager: Initialized voice system manager
    """
    print("[INFO] Initializing Syndicate Voice System...")
    
    try:
        voice_system = VoiceSystemManager()
        
        if voice_system.is_voice_system_available():
            print("[INFO] Syndicate Voice System initialized successfully.")
            return voice_system
        else:
            print("[WARNING] Voice system initialized but TTS is not available.")
            return voice_system
            
    except Exception as e:
        print(f"[ERROR] Failed to initialize voice system: {e}", file=sys.stderr)
        return None


def run_personality_introductions(voice_system):
    """
    Run the personality introductions using the provided voice system.
    
    Args:
        voice_system (VoiceSystemManager): The voice system manager
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not voice_system:
        print("[WARNING] No voice system available for introductions.")
        return False

    if voice_system.is_voice_system_available():
        return voice_system.introduce_personalities()
    else:
        print("[INFO] Voice system not available - introductions skipped.")
        return True # Not an error, just not available