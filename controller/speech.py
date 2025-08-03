import sys
import os
import time
from datetime import datetime
from processor.speech_recognizer import VoskSpeechRecognizer

# --- Configuration ---
# All configuration and environment variable loading is now handled in main.py
MODEL_DIR = os.getenv("VOSK_MODEL_PATH")
LOG_FILE = "logs/speech_log.txt"

# --- Advanced Recognizer Settings from .env ---
# Fallback to default values if not set in .env
SAMPLE_RATE = int(os.getenv("RECOGNIZER_SAMPLE_RATE", 16000))
NOISE_CALIBRATION = float(os.getenv("NOISE_CALIBRATION_DURATION", 2.0))
VAD_AGGRESSIVENESS = int(os.getenv("VAD_AGGRESSIVENESS", 1))
SILENCE_THRESHOLD = float(os.getenv("SILENCE_THRESHOLD", 1.5))
PHRASE_TIMEOUT = float(os.getenv("PHRASE_TIMEOUT", 5.0))


class StatusLogger:
    """A helper class for providing dynamic, single-line status updates in the console."""
    def __init__(self):
        self._last_text_len = 0
        self._spinner_chars = "|/-\\"
        self._spinner_index = 0

    def update(self, text):
        """Updates the status line with new text and a spinner."""
        self._spinner_index = (self._spinner_index + 1) % len(self._spinner_chars)
        spinner = self._spinner_chars[self._spinner_index]
        
        # Prepare the output string
        output = f"\r[{spinner}] Listening... {text}"
        
        # Overwrite the previous line
        sys.stdout.write(output.ljust(self._last_text_len))
        sys.stdout.flush()
        self._last_text_len = len(output)

    def finalize(self, text):
        """Prints a final message and clears the status line."""
        # Clear the line completely and print the final text on a new line
        sys.stdout.write(f"\r{' ' * self._last_text_len}\r")
        sys.stdout.write(f"{text}\n")
        sys.stdout.flush()
        self._last_text_len = 0

    def show_ready(self):
        """Shows the initial ready message."""
        self.update("") # Start with a clean listening line

def start_listening():
    """
    This is the main application loop. It initializes the speech recognizer 
    and processes the transcription output.
    """
    if not MODEL_DIR:
        print("[ERROR] VOSK_MODEL_PATH is not set in the .env file.", file=sys.stderr)
        sys.exit(1)

    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

    try:
        recognizer = VoskSpeechRecognizer(
            model_path=MODEL_DIR,
            samplerate=SAMPLE_RATE,
            vad_aggressiveness=VAD_AGGRESSIVENESS
        )
        
        print(f"[INFO] Speech recognizer initialized with model: {MODEL_DIR}")
        print(f"[INFO] VAD Aggressiveness: {VAD_AGGRESSIVENESS}, Silence Threshold: {SILENCE_THRESHOLD}s")
        print(f"[INFO] Logging complete statements to '{LOG_FILE}'")
        print("[INFO] Press Ctrl+C to stop.")

        status_logger = StatusLogger()
        
        transcription_generator = recognizer.listen_and_transcribe(
            silence_threshold=SILENCE_THRESHOLD,
            phrase_timeout=PHRASE_TIMEOUT,
            calibration_duration=NOISE_CALIBRATION
        )
        
        status_logger.show_ready()

        for result_type, text in transcription_generator:
            if result_type == "partial":
                status_logger.update(text)
            elif result_type == "final" and text:
                timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                log_message = f"[{timestamp}] Finalized: {text}"
                
                status_logger.finalize(log_message)
                
                with open(LOG_FILE, "a") as log_file:
                    log_file.write(log_message + "\n")
                
                # Show the listening status again for the next utterance
                status_logger.show_ready()

    except KeyboardInterrupt:
        print("\n[INFO] Stopping listener...")
    except FileNotFoundError:
        print(f"[ERROR] Model directory not found at '{MODEL_DIR}'.")
        print("[INFO] Please run the 'run.sh' script to download the required model.")
    except Exception as e:
        print(f"\n[ERROR] An unexpected error occurred: {e}", file=sys.stderr)
