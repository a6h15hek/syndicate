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
            samplerate (int): The sample rate for the audio stream. Must be 8000, 16000, 32000, or 48000.
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


    def listen_and_transcribe(self, silence_threshold=1.5, phrase_timeout=4.0, calibration_duration=2.0):
        """
        Captures audio and yields transcription results with VAD-based noise filtering.

        Args:
            silence_threshold (float): Seconds of silence to consider a phrase complete.
            phrase_timeout (float): Maximum seconds for a single phrase before forcing a result.
            calibration_duration (float): Seconds to listen for ambient noise at the start.

        Yields:
            tuple: A tuple containing the result type ('partial' or 'final') and the transcribed text.
        """
        recognizer = vosk.KaldiRecognizer(self.model, self.samplerate)
        
        # The blocksize must be a multiple of the VAD frame size
        with sd.RawInputStream(samplerate=self.samplerate, blocksize=self.vad_frame_size, device=self.device,
                               dtype='int16', channels=1, callback=self._audio_callback):
            
            self._calibrate_noise(calibration_duration)

            last_speech_time = time.time()
            is_speaking = False
            speech_buffer = deque()
            
            while True:
                try:
                    data = self.q.get(timeout=0.1)
                    
                    # Use VAD to check if the frame contains speech
                    is_speech_in_frame = self.vad.is_speech(data, self.samplerate)

                    if is_speech_in_frame:
                        if not is_speaking:
                            is_speaking = True
                        speech_buffer.append(data)
                        last_speech_time = time.time()
                    elif is_speaking:
                        # Not speech, but we were just speaking, so add to buffer briefly
                        speech_buffer.append(data)

                    # Process the buffered audio
                    while speech_buffer:
                        frame = speech_buffer.popleft()
                        if recognizer.AcceptWaveform(frame):
                            result_json = json.loads(recognizer.Result())
                            final_text = result_json.get('text', '')
                            if final_text:
                                yield "final", final_text
                                is_speaking = False
                        else:
                            result_json = json.loads(recognizer.PartialResult())
                            partial_text = result_json.get('partial', '')
                            if partial_text:
                                yield "partial", partial_text
                    
                    # Check for silence timeout to finalize the phrase
                    time_since_last_speech = time.time() - last_speech_time
                    current_partial_text = json.loads(recognizer.PartialResult()).get('partial', '')

                    if is_speaking and time_since_last_speech > silence_threshold:
                        # Silence detected after speech, finalize the phrase
                        is_speaking = False
                        if current_partial_text:
                            yield "final", current_partial_text
                            recognizer.Reset() # Reset to start fresh

                    # Force finalize if the phrase is too long
                    if is_speaking and time_since_last_speech > phrase_timeout:
                        is_speaking = False
                        if current_partial_text:
                            yield "final", current_partial_text
                            recognizer.Reset()


                except queue.Empty:
                    # No audio data, just continue the loop
                    continue
                except Exception as e:
                    print(f"[ERROR] Error in speech recognition stream: {e}", file=sys.stderr)
                    break
