import logging
import sys
from dotenv import load_dotenv

# Specify the path to your custom environment file
# In this case, it's a file named 'tuner' in the same directory
env_path = 'tuner.conf'
load_dotenv(dotenv_path=env_path)

# --- Setup Centralized Logging ---
# Configure logging to capture messages from all modules
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - [%(levelname)s] - (%(module)s) - %(message)s',
    stream=sys.stdout  # Log to standard output
)
log = logging.getLogger(__name__)

# --- Import controllers after logging is configured ---
from controller.voice import VoiceController
from controller import speech

def main():
    """
    Main application entry point.
    Initializes the voice controller, runs personality introductions,
    and starts the main speech recognition loop.
    """
    log.info("Starting The Syndicate application...")
    voice_controller = None
    
    try:
        # --- Initialize Voice System ---
        voice_controller = VoiceController()

        # --- Run Personality Introductions ---
        if voice_controller.is_available():
            log.info("Starting personality introductions...")
            voice_controller.oracle.speak("The path ahead is long. I am Oracle. I will offer guidance, but the journey is yours to walk.")
            voice_controller.kira.speak("You are weak. I am Kira. I will forge you into a weapon. Do not expect kindness.")
            voice_controller.mika.speak("Hello, Master. I'm Mika. I'm here to help you in any way I can. Please don't hesitate to ask.")
            voice_controller.byte.speak("Greetings. I am Byte. I have analyzed all potential risks. Please proceed with caution. I will monitor for threats.")
            voice_controller.quip.speak("Well, look what we have here. Another challenger. I'm Quip. Try to keep up, if you can.")
            voice_controller.wait_for_completion()
            log.info("All personality introductions completed.")
            log.info("The Syndicate is ready to assist.")
        else:
            log.warning("Voice system is not available. Continuing in silent mode.")

        # --- Start Main Application Loop ---
        # The speech controller will handle user interaction.
        # We can pass the voice_controller to it if needed, but for now we assume it's a singleton or handled elsewhere.
        speech.start_listening()

    except KeyboardInterrupt:
        log.info("Application interrupted by user. Shutting down...")
        
    except Exception as e:
        log.critical(f"An unexpected critical error occurred in main: {e}", exc_info=True)
        
    finally:
        # --- Graceful Shutdown ---
        log.info("Initiating shutdown sequence...")
        if voice_controller:
            voice_controller.shutdown()
        
        # Add any other cleanup tasks here
        
        log.info("Application has been shut down.")

if __name__ == "__main__":
    main()
