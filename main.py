# main.py
import logging
from logger_setup import setup_logger
from speech_to_text import SpeechToText
from text_to_speech import TextToSpeech
import config

def on_speech_transcribed(text: str):
    """
    This function is the main logic handler.
    It's called when the STT module transcribes speech.
    """
    print(f"--> YOU SAID: {text}")
    
    # Respond with the fixed phrase using a random voice
    response_text = "Hello Master"
    print(f"--> BOT SAYS: {response_text}")
    tts.speak(response_text, personality=list(config.TTS_VOICES.keys())[0])
    
    # After responding, print a message to indicate it's listening again
    logging.info("Responding complete. Listening for next command...")

if __name__ == "__main__":
    setup_logger()

    # --- Enable Verbose Logging for Coqui TTS ---
    # This will print detailed messages, including model download progress.
    logging.getLogger("TTS").setLevel(logging.DEBUG)

    tts = None
    stt = None
    try:
        logging.info("Starting Voice Assistant...")

        # Initialize TTS and STT modules
        tts = TextToSpeech()
        stt = SpeechToText()

        # Greet with all voices on startup
        greeting = "Hello Master"
        logging.info("Performing voice check with all personalities...")
        for personality in config.TTS_VOICES.keys():
            print(f"--> {personality.upper()} SAYS: {greeting}")
            tts.speak(greeting, personality=personality)
            print(f"--> {personality.upper()} SAID: {greeting}")
        logging.info("Voice check complete.")

        # Start the continuous listening loop and pass the handler function
        logging.info("Ready for your command. Start speaking.")
        stt.listen_and_transcribe(on_speech_transcribed)

    except KeyboardInterrupt:
        logging.info("Program interrupted by user. Shutting down.")
    except Exception as e:
        logging.critical(f"A critical error occurred: {e}")
    finally:
        logging.info("Cleaning up resources...")
        if stt:
            stt.shutdown()
        if tts:
            tts.shutdown()
        logging.info("Shutdown complete.")
