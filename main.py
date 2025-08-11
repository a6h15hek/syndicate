from dotenv import load_dotenv
from controller import speech
import sys
import os

def main():
    """
    Loads environment variables, initializes personality voices,
    and triggers the main application logic from the speech controller.
    """
    # Load environment variables
    load_dotenv()
    
    # Initialize personality voice system
    try:
        print("[INFO] Initializing Syndicate Personality Voice System...")
        
        # Import here to handle potential import errors gracefully
        from processor.tts_synthesizer import PersonalityVoiceManager
        
        voice_manager = PersonalityVoiceManager()
        
        # Create individual personality voice objects as requested
        kira = voice_manager.kira
        mika = voice_manager.mika
        oracle = voice_manager.oracle
        byte = voice_manager.byte
        quip = voice_manager.quip
        
        print("[INFO] Personality voice system initialized successfully.")
        
        # Personality introductions as specifically requested
        print("[INFO] Starting personality introductions...")
        kira.speak("Hello, I'm Kira. How can I assist you today?")
        mika.speak("Hello, I'm Mika. How can I assist you today?")
        oracle.speak("Hello, I'm Oracle. How can I assist you today?")
        byte.speak("Hello, I'm Byte. How can I assist you today?")
        quip.speak("Hello, I'm Quip. How can I assist you today?")
        
        # Wait for all introductions to complete before starting speech recognition
        print("[INFO] Waiting for personality introductions to complete...")
        voice_manager.synthesizer.wait_for_completion()
        
        print("[INFO] The Syndicate is ready. Starting speech recognition...")
        
    except ImportError as e:
        print(f"[WARNING] Could not import TTS components: {e}", file=sys.stderr)
        print("[WARNING] Continuing without voice synthesis...", file=sys.stderr)
        voice_manager = None
        kira = mika = oracle = byte = quip = None
        
    except Exception as e:
        print(f"[ERROR] Failed to initialize personality voice system: {e}", file=sys.stderr)
        print("[WARNING] Continuing without voice synthesis...", file=sys.stderr)
        voice_manager = None
        kira = mika = oracle = byte = quip = None
    
    try:
        # Start the main speech recognition loop
        speech.start_listening()
        
    except KeyboardInterrupt:
        print("\n[INFO] Shutting down application...")
        
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred in main: {e}", file=sys.stderr)
        
    finally:
        # Cleanup voice system if it was initialized
        if voice_manager:
            try:
                voice_manager.shutdown()
                print("[INFO] Voice system shutdown complete.")
            except Exception as cleanup_error:
                print(f"[WARNING] Error during voice system cleanup: {cleanup_error}", file=sys.stderr)

if __name__ == "__main__":
    main()