import sys
import os
from datetime import datetime
from processor.speech_recognizer import VoskSpeechRecognizer

# --- Configuration ---
# Updated to use the medium Indian-English model
MODEL_DIR = "models/vosk-model-en-in-0.5"
LOG_FILE = "logs/speech_log.txt"

def main():
    """
    Main function to initialize the speech recognizer and process the output.
    """
    # Create logs directory if it doesn't exist
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    try:
        # Initialize the speech recognizer
        recognizer = VoskSpeechRecognizer(model_path=MODEL_DIR)
        print("[INFO] Speech recognizer initialized with Indian English model.")
        print(f"[INFO] Logging complete statements to '{LOG_FILE}'")
        print("[INFO] Ready to listen. Press Ctrl+C to stop.")

        # Start listening and processing speech with advanced pause detection
        # silence_threshold: How many seconds of silence determines the end of a phrase.
        # phrase_timeout: How long to listen for a single phrase before finalizing.
        for result_type, text in recognizer.listen_and_transcribe(silence_threshold=2.0, phrase_timeout=5.0):
            if result_type == "partial":
                # Print partial results in real-time for immediate feedback
                # Using carriage return to overwrite the line
                sys.stdout.write(f"\rListening... {text}")
                sys.stdout.flush()
            elif result_type == "final" and text:
                # A complete sentence has been detected after a pause
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                log_message = f"[{timestamp}] Complete Statement: {text}"
                
                # Print the final, organized statement to the console
                # The spaces at the end clear the previous "Listening..." text
                sys.stdout.write(f"\r{log_message}\n")
                sys.stdout.flush()

                # Log the complete statement to a file for record-keeping
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
