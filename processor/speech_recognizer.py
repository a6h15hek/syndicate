import queue
import sounddevice as sd
import vosk
import json
import sys
import os
import time
import webrtcvad
from collections import deque

class VoskSpeechRecognizer:
    """
    A class to handle real-time speech recognition using Vosk, with advanced noise handling
    through Voice Activity Detection (VAD) and configurable settings.
    """

    def __init__(self, model_path, samplerate=16000, device=None, vad_aggressiveness=1):
        """
        Initializes the VoskSpeechRecognizer.

        Args:
            model_path (str): Path to the Vosk model directory.
            samplerate (int): The sample rate for the audio stream. Must match the model's training.
            device (int, optional): Input device ID. Defaults to the system's default device.
            vad_aggressiveness (int): VAD aggressiveness (0-3). 3 is most aggressive.
        """
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model path '{model_path}' not found. Please check the path.")

        self.model = vosk.Model(model_path)
        self.samplerate = samplerate
        self.device = device
        self.q = queue.Queue()
        
        # Initialize VAD
        self.vad = webrtcvad.Vad()
        self.vad.set_mode(vad_aggressiveness)

        # VAD requires audio chunks of 10, 20, or 30 ms. We'll use 30ms.
        self.vad_frame_duration_ms = 30
        self.vad_frame_size = int(self.samplerate * self.vad_frame_duration_ms / 1000)

    def _audio_callback(self, indata, frames, time, status):
        """This is called (from a separate thread) for each audio block."""
        if status:
            print(status, file=sys.stderr)
        self.q.put(bytes(indata))

    def _calibrate_noise(self, duration):
        """Listens for a short period to let the user and environment settle."""
        print(f"[INFO] Calibrating for ambient noise for {duration} seconds. Please be quiet.")
        start_time = time.time()
        while time.time() - start_time < duration:
            # Drain the queue of any initial noise
            try:
                self.q.get_nowait()
            except queue.Empty:
                pass
            time.sleep(0.1)
        print("[INFO] Calibration complete. Ready to listen.")


    def listen_and_transcribe(self, silence_threshold=2.0, phrase_timeout=10.0, calibration_duration=2.0):
        """
        Captures audio and yields transcription results with a robust VAD-based endpointing logic.
        This new logic waits for a clear pause (silence) before finalizing a sentence,
        preventing premature cut-offs during natural conversation.

        Args:
            silence_threshold (float): Seconds of silence to consider a phrase complete.
            phrase_timeout (float): Maximum seconds for a single phrase before forcing a result.
            calibration_duration (float): Seconds to listen for ambient noise at the start.

        Yields:
            tuple: A tuple containing the result type ('partial' or 'final') and the transcribed text.
        """
        recognizer = vosk.KaldiRecognizer(self.model, self.samplerate)
        
        # The blocksize must be a multiple of the VAD frame size for webrtcvad
        with sd.RawInputStream(samplerate=self.samplerate, blocksize=self.vad_frame_size, device=self.device,
                               dtype='int16', channels=1, callback=self._audio_callback):
            
            self._calibrate_noise(calibration_duration)

            is_speaking = False
            last_speech_time = time.time()
            phrase_start_time = time.time()
            
            while True:
                try:
                    # Use a timeout to allow checking for silence even when no new audio comes in
                    data = self.q.get(timeout=0.1)
                    
                    is_speech_in_frame = self.vad.is_speech(data, self.samplerate)

                    # Process the audio frame
                    if recognizer.AcceptWaveform(data):
                        # This is an intermediate result from Vosk. We get the partial text but
                        # wait for our own silence detection to finalize the full utterance.
                        partial_result = json.loads(recognizer.PartialResult())
                        if partial_result.get('partial'):
                            yield "partial", partial_result['partial']
                    
                    if is_speech_in_frame:
                        if not is_speaking:
                            # Detected start of a new phrase
                            is_speaking = True
                            phrase_start_time = time.time()
                        last_speech_time = time.time()

                except queue.Empty:
                    # No new audio. This is where we check if a phrase has ended.
                    pass
                except Exception as e:
                    print(f"[ERROR] Error in speech recognition stream: {e}", file=sys.stderr)
                    break

                # Check for end-of-speech conditions ONLY if we have been speaking.
                if is_speaking:
                    time_since_last_speech = time.time() - last_speech_time
                    phrase_duration = time.time() - phrase_start_time
                    
                    # FINALIZATION LOGIC:
                    # A phrase is considered final if EITHER:
                    # 1. A period of silence is detected (time_since_last_speech > silence_threshold)
                    # 2. The phrase has been going on for too long (phrase_duration > phrase_timeout)
                    if time_since_last_speech > silence_threshold or phrase_duration > phrase_timeout:
                        # Use FinalResult() which gets the best possible transcription and resets the recognizer.
                        final_result_json = json.loads(recognizer.FinalResult())
                        final_text = final_result_json.get('text', '')
                        
                        if final_text:
                            yield "final", final_text
                        
                        # Reset state for the next utterance.
                        is_speaking = False

