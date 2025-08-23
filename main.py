import logging
import sys
from dotenv import load_dotenv

# --- Early initialization to load environment variables ---
load_dotenv()

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
            voice_controller.introduce_personalities()
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
