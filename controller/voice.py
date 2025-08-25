import os
import logging
import time
from processor.tts_synthesizer import PersonalityVoiceSynthesizer

# --- Setup Logging ---
log = logging.getLogger(__name__)

class VoiceController:
    """
    Manages the Text-to-Speech (TTS) system, providing a clean interface
    for making different personalities speak. It handles the initialization
    of the synthesizer and provides access to individual personality voices.
    """
    PERSONALITIES = ['kira', 'mika', 'oracle', 'byte', 'quip']

    def __init__(self):
        """Initializes the VoiceController."""
        log.info("Initializing Voice Controller...")
        
        self.tts_enabled = os.getenv("TTS_ENABLED", "true").lower() == "true"
        device_id = os.getenv("TTS_DEVICE")
        self.warmup_on_init = os.getenv("TTS_WARMUP_ON_INIT", "true").lower() == "true"

        self.synthesizer = None
        self.personality_configs = {}

        if self.tts_enabled:
            try:
                self.personality_configs = self._load_personality_configs()
                self.synthesizer = PersonalityVoiceSynthesizer(device=device_id)
                self._create_personality_voices()

                if self.warmup_on_init:
                    self._warmup_voices()

                log.info("Voice Controller initialized successfully.")
            except Exception as e:
                log.error(f"Failed to initialize the TTS synthesizer: {e}", exc_info=True)
        else:
            log.info("TTS is disabled. Voice Controller will operate in silent mode.")

    def _load_personality_configs(self):
        """Loads voice configurations for all personalities from environment variables."""
        configs = {}
        for p in self.PERSONALITIES:
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

    def _create_personality_voices(self):
        """Creates individual voice objects for each personality."""
        for p_name in self.PERSONALITIES:
            setattr(self, p_name, PersonalityVoice(p_name, self))
        log.debug("Individual personality voice objects created.")

    def _warmup_voices(self):
        """Warms up the TTS engine for each personality to reduce latency on first request."""
        if not self.is_available():
            return
        log.info("Warming up personality voices...")
        for name, config in self.personality_configs.items():
            if config.get('speaker'):
                log.info(f"Warming up voice for {name.upper()}...")
                # Synthesize a short, silent-like text to trigger model loading.
                self.synthesizer.speak(" ", name, config)
        self.wait_for_completion()
        log.info("All voices are warm and ready.")

    def is_available(self):
        """Checks if the TTS system is available and ready."""
        return self.synthesizer is not None

    def speak(self, personality_name, text):
        """
        Makes a specific personality speak the given text.

        Args:
            personality_name (str): The name of the personality.
            text (str): The text to be spoken.
        """
        if not self.is_available():
            log.warning(f"TTS not available. Cannot speak as {personality_name}.")
            return
            
        if personality_name not in self.personality_configs:
            log.error(f"Unknown personality: {personality_name}")
            return

        log.info(f"Queuing speech for {personality_name.upper()}: '{text}'")
        config = self.personality_configs[personality_name]
        self.synthesizer.speak(text, personality_name, config)

    def wait_for_completion(self):
        """Waits for all currently queued speech to finish playing."""
        if self.is_available():
            self.synthesizer.wait_for_completion()

    def shutdown(self):
        """Shuts down the TTS system gracefully."""
        if self.is_available():
            log.info("Shutting down the voice controller and synthesizer.")
            self.synthesizer.shutdown()
        else:
            log.info("Voice controller was not initialized, nothing to shut down.")


class PersonalityVoice:
    """
    A simple wrapper class representing an individual personality's voice,
    providing a clean `speak()` method.
    """
    def __init__(self, name, controller):
        self.name = name
        self.controller = controller

    def speak(self, text):
        """
        Makes this personality speak the given text.

        Args:
            text (str): The text to speak.
        """
        self.controller.speak(self.name, text)
