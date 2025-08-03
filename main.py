import sys
import os
from datetime import datetime
from dotenv import load_dotenv
from processor.speech_recognizer import VoskSpeechRecognizer

# --- Load Environment Variables ---
# Load variables from the .env file into the environment
load_dotenv()

# --- Configuration ---
# Get the model path from environment variables.
# This makes the application more flexible and avoids hardcoding paths.
MODEL_DIR = os.getenv("VOSK_MODEL_PATH")
LOG_FILE = "logs/speech_log.txt"

def main():
    """
    Main function to initialize the speech recognizer and process the output.
    """
    # --- Pre-run Checks ---
    # Ensure the model path is actually set in the .env file before proceeding.
    if not MODEL_DIR:
        print("[ERROR] VOSK_MODEL_PATH is not set in the .env file.", file=sys.stderr)
        print("[INFO] Please ensure a .env file exists with the VOSK_MODEL_PATH variable.", file=sys.stderr)
        sys.exit(1)

    # Create logs directory if it doesn't exist to prevent errors on first run.
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    try:
        # Initialize the speech recognizer with the path from the .env file.
        recognizer = VoskSpeechRecognizer(model_path=MODEL_DIR)
        print(f"[INFO] Speech recognizer initialized with model: {MODEL_DIR}")
        print(f"[INFO] Logging complete statements to '{LOG_FILE}'")
        print("[INFO] Ready to listen. Press Ctrl+C to stop.")

        # Start listening and processing speech with advanced pause detection.
        # silence_threshold: How many seconds of silence determines the end of a phrase.
        # phrase_timeout: How long to listen for a single phrase before finalizing.
        for result_type, text in recognizer.listen_and_transcribe(silence_threshold=2.0, phrase_timeout=5.0):
            if result_type == "partial":
                # Print partial results in real-time for immediate feedback.
                # Using carriage return to overwrite the line for a cleaner look.
                sys.stdout.write(f"\rListening... {text}")
                sys.stdout.flush()
            elif result_type == "final" and text:
                # A complete sentence has been detected after a pause.
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                log_message = f"[{timestamp}] Complete Statement: {text}"
                
                # Print the final, organized statement to the console.
                # The spaces at the end clear the previous "Listening..." text.
                sys.stdout.write(f"\r{log_message}              \n")
                sys.stdout.flush()

                # Log the complete statement to a file for record-keeping.
                with open(LOG_FILE, "a") as log_file:
                    log_file.write(log_message + "\n")

    except KeyboardInterrupt:
        print("\n[INFO] Stopping listener...")
    except FileNotFoundError:
        print(f"[ERROR] Model directory not found at '{MODEL_DIR}'.")
        print("[INFO] Please run the 'run.sh' script to download the required model.")
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
