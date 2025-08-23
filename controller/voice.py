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

    def __init__(self):
        """Initializes the VoiceController."""
        log.info("Initializing Voice Controller...")
        
        # --- Configuration from .env ---
        self.tts_enabled = os.getenv("TTS_ENABLED", "true").lower() == "true"
        self.introductions_enabled = os.getenv("TTS_INTRODUCTION_ENABLED", "true").lower() == "true"
        device_id = os.getenv("TTS_DEVICE")

        self.synthesizer = None
        if self.tts_enabled:
            try:
                self.synthesizer = PersonalityVoiceSynthesizer(device=device_id)
                self._create_personality_voices()
                log.info("Voice Controller initialized successfully.")
            except Exception as e:
                log.error(f"Failed to initialize the TTS synthesizer: {e}", exc_info=True)
        else:
            log.info("TTS is disabled. Voice Controller will operate in silent mode.")

    def _create_personality_voices(self):
        """Creates individual voice objects for each personality."""
        self.kira = PersonalityVoice('kira', self)
        self.mika = PersonalityVoice('mika', self)
        self.oracle = PersonalityVoice('oracle', self)
        self.byte = PersonalityVoice('byte', self)
        self.quip = PersonalityVoice('quip', self)
        log.debug("Individual personality voice objects created.")

    def is_available(self):
        """Checks if the TTS system is available and ready."""
        return self.synthesizer is not None

    def introduce_personalities(self):
        """Has all personalities introduce themselves sequentially."""
        if not self.is_available():
            log.warning("Cannot run introductions; TTS system is not available.")
            return

        if not self.introductions_enabled:
            log.info("Personality introductions are disabled in the configuration.")
            return
            
        log.info("Starting personality introductions...")
        
        try:
            # Introductions are queued and will play sequentially
            self.oracle.speak("Greetings. I am Oracle, keeper of wisdom and foresight.")
            self.kira.speak("I am Kira. I will push you to your limits. Expect no mercy.")
            self.mika.speak("Hello! I'm Mika. I'm here to support you with all my heart.")
            self.byte.speak("Um, hi... I'm Byte. I'll try my best to help with any questions.")
            self.quip.speak("Hey there! Quip's the name, wit's the game. Ready for some fun?")
            
            # Wait for all introductions to complete
            self.wait_for_completion()
            log.info("All personality introductions completed.")
            
        except Exception as e:
            log.error(f"An error occurred during personality introductions: {e}", exc_info=True)

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
            
        if not hasattr(self, personality_name):
            log.error(f"Unknown personality: {personality_name}")
            return

        log.info(f"Queuing speech for {personality_name.upper()}: '{text}'")
        self.synthesizer.speak(text, personality_name)

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
