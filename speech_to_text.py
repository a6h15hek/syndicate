# speech_to_text.py
import logging
import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel
import config

class SpeechToText:
    """Handles continuous listening and transcription using Whisper."""

    def __init__(self):
        logging.info("Initializing SpeechToText...")
        self.model = WhisperModel(
            config.STT_MODEL_SIZE,
            device=config.STT_DEVICE,
            compute_type=config.STT_COMPUTE_TYPE
        )
        logging.info(f"Whisper model '{config.STT_MODEL_SIZE}' loaded on {config.STT_DEVICE}.")
        self.audio_buffer = np.array([], dtype=np.float32)
        self.silence_counter = 0

    def _is_silent(self, audio_chunk):
        """Checks if a chunk of audio is silent."""
        rms = np.sqrt(np.mean(audio_chunk**2))
        return rms < config.AUDIO_SILENCE_THRESHOLD

    def listen_and_transcribe(self, callback):
        """
        Listens continuously from the microphone and calls the callback with transcribed text.
        This function runs forever until the program is stopped.
        """
        logging.info("Starting continuous listening loop...")
        
        def audio_callback(indata, frames, time, status):
            """This function is called for each audio chunk from the microphone."""
            if status:
                logging.warning(f"Audio callback status: {status}")

            is_silent_chunk = self._is_silent(indata)

            if not is_silent_chunk:
                # Append audio chunk if it's not silent
                self.audio_buffer = np.concatenate((self.audio_buffer, indata.flatten()))
                self.silence_counter = 0
            else:
                # If we have recorded speech and now detect silence
                if len(self.audio_buffer) > 0:
                    self.silence_counter += 1
                    silence_duration = (self.silence_counter * config.AUDIO_BLOCK_DURATION_SECONDS * 1000) / (config.AUDIO_SAMPLE_RATE / 1000)
                    
                    if silence_duration >= config.AUDIO_SILENCE_DURATION_SECONDS:
                        logging.info("End of speech detected. Transcribing...")
                        segments, info = self.model.transcribe(self.audio_buffer, vad_filter=True)
                        
                        transcribed_text = "".join(segment.text for segment in segments).strip()
                        
                        if transcribed_text:
                            logging.info(f"Transcription successful: '{transcribed_text}'")
                            callback(transcribed_text) # Call the main logic with the text
                        
                        # Reset buffer after transcription
                        self.audio_buffer = np.array([], dtype=np.float32)
                        self.silence_counter = 0

        try:
            with sd.InputStream(
                callback=audio_callback,
                samplerate=config.AUDIO_SAMPLE_RATE,
                channels=1,
                blocksize=int(config.AUDIO_SAMPLE_RATE * config.AUDIO_BLOCK_DURATION_SECONDS / 10) # Smaller blocks for faster VAD
            ):
                while True:
                    # The audio_callback runs in a separate thread, so we just wait here
                    sd.sleep(1000)
        except Exception as e:
            logging.error(f"An error occurred in the listening loop: {e}")