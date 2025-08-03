import sys
from datetime import datetime
from processor.speech_recognizer import VoskSpeechRecognizer

# --- Configuration ---
MODEL_DIR = "models/vosk-model-small-en-us-0.15"
LOG_FILE = "speech_log.txt"

def main():
    """
    Main function to initialize the speech recognizer and process the output.
    """
    try:
        # Initialize the speech recognizer
        recognizer = VoskSpeechRecognizer(model_path=MODEL_DIR)
        print("[INFO] Speech recognizer initialized.")
        print(f"[INFO] Logging complete statements to '{LOG_FILE}'")
        print("[INFO] Ready to listen. Press Ctrl+C to stop.")

        # Start listening and processing speech
        for result_type, text in recognizer.listen_and_transcribe():
            if result_type == "partial":
                # Print partial results in real-time
                sys.stdout.write(f"Listening... {text}\r")
                sys.stdout.flush()
            elif result_type == "final" and text:
                # A complete sentence has been detected
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                log_message = f"[{timestamp}] Complete Statement: {text}"
                
                # Print to console and clear the line
                # The spaces at the end clear the previous "Listening..." text
                sys.stdout.write(f"{log_message}\n")
                sys.stdout.flush()

                # Log the complete statement to a file
                with open(LOG_FILE, "a") as log_file:
                    log_file.write(log_message + "\n")

    except KeyboardInterrupt:
        print("\n[INFO] Stopping...")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
