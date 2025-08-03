import queue
import sounddevice as sd
import vosk
import json
import sys
import os
import time

class VoskSpeechRecognizer:
    """
    A class to handle real-time speech recognition using Vosk with advanced pause detection.
    """

    def __init__(self, model_path, device=None, samplerate=None):
        """
        Initializes the VoskSpeechRecognizer.

        Args:
            model_path (str): Path to the Vosk model directory.
            device (int, optional): Input device ID. Defaults to default device.
            samplerate (int, optional): The sample rate for the audio stream.
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model path '{model_path}' not found. Please check the path or run the setup script.")

        self.model = vosk.Model(model_path)
        self.device = device
        self.samplerate = samplerate
        self.q = queue.Queue()

        if self.samplerate is None:
            try:
                device_info = sd.query_devices(self.device, 'input')
                self.samplerate = int(device_info['default_samplerate'])
            except Exception as e:
                print(f"[ERROR] Could not query audio device: {e}")
                print("[INFO] Please ensure you have a microphone connected.")
                sys.exit(1)


    def _audio_callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status, file=sys.stderr)
        self.q.put(bytes(indata))

    def listen_and_transcribe(self, silence_threshold=2.0, phrase_timeout=4.0):
        """
        Captures audio and yields transcription results with intelligent pause detection.

        This method listens for speech and determines the end of a statement based on
        a period of silence, rather than just waiting for the user to stop talking entirely.

        Args:
            silence_threshold (float): Seconds of silence to consider a phrase complete.
            phrase_timeout (float): Maximum seconds for a single phrase before forcing a result.

        Yields:
            tuple: A tuple containing the result type ('partial' or 'final') and the transcribed text.
        """
        try:
            recognizer = vosk.KaldiRecognizer(self.model, self.samplerate)
            
            with sd.RawInputStream(samplerate=self.samplerate, blocksize=8000, device=self.device,
                                   dtype='int16', channels=1, callback=self._audio_callback):
                
                last_partial_text = ""
                last_speech_time = time.time()

                while True:
                    data = self.q.get()
                    
                    # Process audio data
                    if recognizer.AcceptWaveform(data):
                        # Vosk detected a definitive end of speech (e.g., long pause)
                        result_json = json.loads(recognizer.Result())
                        final_text = result_json.get('text', '')
                        if final_text:
                            yield "final", final_text
                            last_partial_text = ""
                            last_speech_time = time.time()
                    else:
                        # User is potentially still speaking or has paused briefly
                        result_json = json.loads(recognizer.PartialResult())
                        partial_text = result_json.get('partial', '')
                        
                        # Check if there is new speech
                        if partial_text and partial_text != last_partial_text:
                            # New speech detected, update time and text
                            last_speech_time = time.time()
                            last_partial_text = partial_text
                            yield "partial", partial_text
                        
                        # Check for silence timeout to finalize the phrase
                        is_silence = time.time() - last_speech_time > silence_threshold
                        is_phrase_timeout = time.time() - last_speech_time > phrase_timeout
                        
                        if (is_silence or is_phrase_timeout) and last_partial_text:
                            # Silence detected, treat the last partial text as final
                            yield "final", last_partial_text
                            # Reset for the next utterance
                            last_partial_text = ""
                            recognizer.Reset()
                            last_speech_time = time.time()

        except Exception as e:
            print(f"[ERROR] Error in speech recognition stream: {e}", file=sys.stderr)


def list_audio_devices():
    """A helper function to list available audio devices."""
    print("Available audio devices:")
    print(sd.query_devices())
