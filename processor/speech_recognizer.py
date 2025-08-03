import queue
import sounddevice as sd
import vosk
import json
import sys
import os

class VoskSpeechRecognizer:
    """A class to handle real-time speech recognition using Vosk."""

    def __init__(self, model_path, device=None, samplerate=None):
        """
        Initializes the VoskSpeechRecognizer.

        Args:
            model_path (str): Path to the Vosk model directory.
            device (str, optional): Input device name or ID. Defaults to None.
            samplerate (int, optional): The sample rate for the audio stream. Defaults to None.
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model path '{model_path}' not found. Please check the path.")

        self.model = vosk.Model(model_path)
        self.device = device
        self.samplerate = samplerate
        self.q = queue.Queue()

        if self.samplerate is None:
            device_info = sd.query_devices(self.device, 'input')
            self.samplerate = int(device_info['default_samplerate'])

    def _audio_callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status, file=sys.stderr)
        self.q.put(bytes(indata))

    def listen_and_transcribe(self):
        """
        Captures audio and yields transcription results.

        Yields:
            tuple: A tuple containing the result type ('partial' or 'final') and the transcribed text.
        """
        try:
            recognizer = vosk.KaldiRecognizer(self.model, self.samplerate)
            
            with sd.RawInputStream(samplerate=self.samplerate, blocksize=8000, device=self.device,
                                   dtype='int16', channels=1, callback=self._audio_callback):
                
                while True:
                    data = self.q.get()
                    if recognizer.AcceptWaveform(data):
                        result_json = json.loads(recognizer.Result())
                        final_text = result_json.get('text', '')
                        yield "final", final_text
                    else:
                        result_json = json.loads(recognizer.PartialResult())
                        partial_text = result_json.get('partial', '')
                        yield "partial", partial_text
        except Exception as e:
            print(f"[ERROR] Error in speech recognition stream: {e}", file=sys.stderr)


def list_audio_devices():
    """A helper function to list available audio devices."""
    print("Available audio devices:")
    print(sd.query_devices())

