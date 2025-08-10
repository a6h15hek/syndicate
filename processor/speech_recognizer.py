import queue
import sounddevice as sd
import vosk
import json
import sys
import os
import time
import webrtcvad
import numpy as np
import logging
import threading
from collections import deque
from typing import Generator, Tuple, Optional, Dict, Any
import re
from concurrent.futures import ThreadPoolExecutor
import warnings

# Suppress warnings for cleaner output
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=RuntimeWarning)

class AudioProcessor:
    """Advanced audio processing with noise suppression and echo cancellation."""
    
    def __init__(self, sample_rate: int, enable_noise_suppression: bool = True,
                 noise_suppression_level: float = 0.3, enable_echo_cancellation: bool = True):
        self.sample_rate = sample_rate
        self.enable_noise_suppression = enable_noise_suppression
        self.noise_suppression_level = noise_suppression_level
        self.enable_echo_cancellation = enable_echo_cancellation
        
        # Noise suppression parameters
        self.noise_profile = None
        self.noise_samples = deque(maxlen=50)  # Store recent samples for noise profiling
        
        # Echo cancellation parameters
        self.echo_buffer = deque(maxlen=100)
        
    def process_audio(self, audio_data: np.ndarray) -> np.ndarray:
        """Process audio data with noise suppression and echo cancellation."""
        try:
            if self.enable_noise_suppression:
                audio_data = self._suppress_noise(audio_data)
            
            if self.enable_echo_cancellation:
                audio_data = self._cancel_echo(audio_data)
                
            return audio_data
        except Exception as e:
            logging.warning(f"Audio processing failed: {e}")
            return audio_data
    
    def _suppress_noise(self, audio_data: np.ndarray) -> np.ndarray:
        """Apply noise suppression using spectral subtraction."""
        try:
            # Simple noise suppression using moving average
            if len(self.noise_samples) > 10:
                noise_level = np.mean([np.mean(np.abs(sample)) for sample in self.noise_samples])
                signal_level = np.mean(np.abs(audio_data))
                
                if signal_level > noise_level * 2:  # Signal is significantly above noise
                    # Apply gentle noise gate
                    threshold = noise_level * (1 + self.noise_suppression_level)
                    mask = np.abs(audio_data) > threshold
                    audio_data = audio_data * mask
            
            # Store sample for noise profiling
            self.noise_samples.append(audio_data.copy())
            return audio_data
        except Exception:
            return audio_data
    
    def _cancel_echo(self, audio_data: np.ndarray) -> np.ndarray:
        """Simple echo cancellation."""
        try:
            # Store in echo buffer
            self.echo_buffer.append(audio_data.copy())
            
            # Simple echo suppression by comparing with previous samples
            if len(self.echo_buffer) > 5:
                correlation_threshold = 0.8
                for i in range(1, min(6, len(self.echo_buffer))):
                    prev_sample = self.echo_buffer[-i-1]
                    if len(prev_sample) == len(audio_data):
                        correlation = np.corrcoef(audio_data.flatten(), prev_sample.flatten())[0, 1]
                        if not np.isnan(correlation) and correlation > correlation_threshold:
                            # High correlation indicates potential echo
                            audio_data = audio_data - prev_sample * 0.3
                            break
            
            return audio_data
        except Exception:
            return audio_data


class VoiceActivityDetector:
    """Enhanced Voice Activity Detection with dynamic thresholds."""
    
    def __init__(self, sample_rate: int, vad_aggressiveness: int = 2,
                 energy_threshold: float = 800, dynamic_threshold: bool = True):
        self.sample_rate = sample_rate
        self.vad = webrtcvad.Vad()
        self.vad.set_mode(vad_aggressiveness)
        
        self.energy_threshold = energy_threshold
        self.dynamic_threshold = dynamic_threshold
        self.dynamic_energy_adjustment_damping = float(os.getenv("DYNAMIC_ENERGY_ADJUSTMENT_DAMPING", 0.15))
        self.dynamic_energy_ratio = float(os.getenv("DYNAMIC_ENERGY_RATIO", 1.5))
        
        # Dynamic threshold parameters
        self.ambient_energy = energy_threshold
        self.energy_samples = deque(maxlen=100)
        
        # VAD frame requirements
        self.vad_frame_duration_ms = 30
        self.vad_frame_size = int(sample_rate * self.vad_frame_duration_ms / 1000)
    
    def is_speech(self, audio_data: bytes) -> bool:
        """Determine if audio contains speech using multiple methods."""
        try:
            # WebRTC VAD
            webrtc_result = self.vad.is_speech(audio_data, self.sample_rate)
            
            # Energy-based detection
            audio_np = np.frombuffer(audio_data, dtype=np.int16)
            energy = np.sqrt(np.mean(audio_np.astype(np.float32) ** 2))
            
            # Update dynamic threshold
            if self.dynamic_threshold:
                self._update_dynamic_threshold(energy)
                energy_result = energy > (self.ambient_energy * self.dynamic_energy_ratio)
            else:
                energy_result = energy > self.energy_threshold
            
            # Combine results (both methods must agree for high confidence)
            return webrtc_result and energy_result
        except Exception as e:
            logging.debug(f"VAD error: {e}")
            return False
    
    def _update_dynamic_threshold(self, energy: float):
        """Update dynamic energy threshold based on ambient noise."""
        self.energy_samples.append(energy)
        
        if len(self.energy_samples) > 10:
            # Use running average of lower percentile as ambient energy
            sorted_energies = sorted(self.energy_samples)
            ambient_estimate = np.mean(sorted_energies[:len(sorted_energies)//3])  # Bottom third
            
            # Smooth adjustment
            self.ambient_energy = (
                self.ambient_energy * (1 - self.dynamic_energy_adjustment_damping) +
                ambient_estimate * self.dynamic_energy_adjustment_damping
            )


class TextProcessor:
    """Advanced text processing with grammar correction and vocabulary enhancement."""
    
    def __init__(self, custom_vocabulary_path: Optional[str] = None):
        self.custom_vocabulary = {}
        self.priority_names = {}
        self.common_corrections = {}
        self.technical_terms = {}
        
        if custom_vocabulary_path and os.path.exists(custom_vocabulary_path):
            try:
                with open(custom_vocabulary_path, 'r', encoding='utf-8') as f:
                    vocab_data = json.load(f)
                    self.priority_names = vocab_data.get('priority_names', {})
                    self.common_corrections = vocab_data.get('common_corrections', {})
                    self.technical_terms = vocab_data.get('technical_terms', {})
                    self.custom_vocabulary = {**self.priority_names, **self.technical_terms}
                logging.info(f"Loaded custom vocabulary with {len(self.custom_vocabulary)} entries")
            except Exception as e:
                logging.warning(f"Failed to load custom vocabulary: {e}")
    
    def process_text(self, text: str) -> str:
        """Process text with corrections and enhancements."""
        if not text.strip():
            return text
        
        try:
            # Apply custom vocabulary replacements
            text = self._apply_vocabulary_corrections(text)
            
            # Apply common spelling corrections
            text = self._apply_spelling_corrections(text)
            
            # Normalize text
            text = self._normalize_text(text)
            
            # Apply grammar improvements
            text = self._improve_grammar(text)
            
            return text.strip()
        except Exception as e:
            logging.debug(f"Text processing error: {e}")
            return text
    
    def _apply_vocabulary_corrections(self, text: str) -> str:
        """Apply custom vocabulary corrections."""
        # Case-insensitive replacement for custom vocabulary
        text_lower = text.lower()
        for incorrect, correct in self.custom_vocabulary.items():
            # Use word boundaries to avoid partial matches
            pattern = r'\b' + re.escape(incorrect.lower()) + r'\b'
            text = re.sub(pattern, correct, text, flags=re.IGNORECASE)
        
        return text
    
    def _apply_spelling_corrections(self, text: str) -> str:
        """Apply common spelling corrections."""
        for incorrect, correct in self.common_corrections.items():
            pattern = r'\b' + re.escape(incorrect) + r'\b'
            text = re.sub(pattern, correct, text, flags=re.IGNORECASE)
        
        return text
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text formatting."""
        # Remove extra spaces
        text = re.sub(r'\s+', ' ', text)
        
        # Fix common punctuation issues
        text = re.sub(r'\s+([.,!?;:])', r'\1', text)
        text = re.sub(r'([.,!?;:])\s*([a-zA-Z])', r'\1 \2', text)
        
        # Capitalize first letter of sentences
        sentences = re.split(r'([.!?]+\s*)', text)
        normalized_sentences = []
        
        for i, sentence in enumerate(sentences):
            if i % 2 == 0 and sentence.strip():  # Actual sentence content
                sentence = sentence.strip()
                if sentence:
                    sentence = sentence[0].upper() + sentence[1:] if len(sentence) > 1 else sentence.upper()
            normalized_sentences.append(sentence)
        
        return ''.join(normalized_sentences).strip()
    
    def _improve_grammar(self, text: str) -> str:
        """Apply basic grammar improvements."""
        # Fix common grammar issues
        grammar_fixes = {
            r'\bi\b': 'I',  # Capitalize standalone 'i'
            r'\bim\b': "I'm",  # Fix common contraction
            r'\bdont\b': "don't",
            r'\bcant\b': "can't",
            r'\bwont\b': "won't",
            r'\bisnt\b': "isn't",
            r'\barent\b': "aren't",
            r'\bwasnt\b': "wasn't",
            r'\bwerent\b': "weren't",
            r'\bhasnt\b': "hasn't",
            r'\bhavent\b': "haven't",
            r'\bdidnt\b': "didn't",
            r'\bdoesnt\b': "doesn't"
        }
        
        for pattern, replacement in grammar_fixes.items():
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text


class EnhancedVoskSpeechRecognizer:
    """Enhanced Vosk Speech Recognizer with advanced features."""
    
    def __init__(self, model_path: str, samplerate: int = 16000, device: Optional[int] = None):
        """Initialize the enhanced speech recognizer."""
        self._validate_model_path(model_path)
        
        # Core components
        self.model = vosk.Model(model_path)
        self.samplerate = samplerate
        self.device = device
        self.audio_queue = queue.Queue()
        
        # Load configuration from environment
        self._load_config()
        
        # Initialize processors
        self.audio_processor = AudioProcessor(
            samplerate,
            self.enable_noise_suppression,
            self.noise_suppression_level,
            self.enable_echo_cancellation
        )
        
        self.vad = VoiceActivityDetector(
            samplerate,
            self.vad_aggressiveness,
            self.energy_threshold,
            self.dynamic_energy_threshold
        )
        
        self.text_processor = TextProcessor(
            self.custom_vocabulary_path if self.enable_custom_vocabulary else None
        )
        
        # State management
        self.is_listening = False
        self.stats = {
            'total_phrases': 0,
            'successful_recognitions': 0,
            'failed_recognitions': 0,
            'average_confidence': 0.0
        }
        
        # Threading
        self.executor = ThreadPoolExecutor(max_workers=self.num_worker_threads)
        
        # Setup logging
        self._setup_logging()
    
    def _validate_model_path(self, model_path: str):
        """Validate that the model path exists and is accessible."""
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model path '{model_path}' not found. Please check the path.")
        
        # Check if model files exist
        required_files = ['am/final.mdl', 'graph/HCLG.fst', 'words.txt']
        for file_path in required_files:
            full_path = os.path.join(model_path, file_path)
            if not os.path.exists(full_path):
                logging.warning(f"Model file {file_path} not found, model might be incomplete")
    
    def _load_config(self):
        """Load configuration from environment variables."""
        self.chunk_size = int(os.getenv("AUDIO_CHUNK_SIZE", 480))
        self.energy_threshold = float(os.getenv("ENERGY_THRESHOLD", 800))
        self.dynamic_energy_threshold = os.getenv("DYNAMIC_ENERGY_THRESHOLD", "true").lower() == "true"
        self.vad_aggressiveness = int(os.getenv("VAD_AGGRESSIVENESS", 2))
        
        self.min_speech_duration = float(os.getenv("MIN_SPEECH_DURATION", 0.3))
        self.max_silence_in_speech = float(os.getenv("MAX_SILENCE_IN_SPEECH", 0.8))
        self.speech_padding_before = float(os.getenv("SPEECH_PADDING_BEFORE", 0.2))
        self.speech_padding_after = float(os.getenv("SPEECH_PADDING_AFTER", 0.2))
        
        self.min_confidence_threshold = float(os.getenv("MIN_CONFIDENCE_THRESHOLD", 0.3))
        self.enable_confidence_filtering = os.getenv("ENABLE_CONFIDENCE_FILTERING", "true").lower() == "true"
        
        self.enable_grammar_correction = os.getenv("ENABLE_GRAMMAR_CORRECTION", "true").lower() == "true"
        self.enable_spell_check = os.getenv("ENABLE_SPELL_CHECK", "true").lower() == "true"
        self.enable_custom_vocabulary = os.getenv("ENABLE_CUSTOM_VOCABULARY", "true").lower() == "true"
        self.custom_vocabulary_path = os.getenv("CUSTOM_VOCABULARY_PATH", "config/custom_vocabulary.json")
        
        self.enable_noise_suppression = os.getenv("ENABLE_NOISE_SUPPRESSION", "true").lower() == "true"
        self.noise_suppression_level = float(os.getenv("NOISE_SUPPRESSION_LEVEL", 0.3))
        self.enable_echo_cancellation = os.getenv("ENABLE_ECHO_CANCELLATION", "true").lower() == "true"
        
        self.num_worker_threads = int(os.getenv("NUM_WORKER_THREADS", 2))
        self.buffer_size = int(os.getenv("AUDIO_BUFFER_SIZE", 50))
        self.enable_recovery_mode = os.getenv("ENABLE_RECOVERY_MODE", "true").lower() == "true"
        self.max_retries = int(os.getenv("MAX_RETRIES", 3))
        self.retry_delay = float(os.getenv("RETRY_DELAY", 1.0))
    
    def _setup_logging(self):
        """Setup logging configuration."""
        log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper())
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),
                logging.FileHandler('logs/speech_recognition.log', mode='a')
            ]
        )
        
        # Ensure log directory exists
        os.makedirs('logs', exist_ok=True)
    
    def _audio_callback(self, indata, frames, time_info, status):
        """Enhanced audio callback with error handling."""
        if status:
            if status.input_underflow:
                logging.debug("Audio input underflow")
            elif status.input_overflow:
                logging.warning("Audio input overflow - consider increasing buffer size")
            else:
                logging.warning(f"Audio callback status: {status}")
        
        try:
            # Convert the CFFI buffer to a NumPy array for processing.
            # The stream is opened with dtype='int16', so we use that here.
            audio_data_np = np.frombuffer(indata, dtype=np.int16)
            
            # Apply audio processing
            processed_audio = self.audio_processor.process_audio(audio_data_np)
            
            # Add to queue if not full. The queue expects bytes.
            if self.audio_queue.qsize() < self.buffer_size:
                self.audio_queue.put(bytes(processed_audio), block=False)
            else:
                logging.debug("Audio buffer full, dropping frame")
        
        except Exception as e:
            logging.error(f"Audio callback error: {e}")
    
    def _calibrate_environment(self, duration: float):
        """Enhanced environment calibration."""
        logging.info(f"Calibrating environment for {duration} seconds...")
        logging.info("Please remain quiet during calibration for optimal results.")
        
        start_time = time.time()
        calibration_samples = []
        
        while time.time() - start_time < duration:
            try:
                data = self.audio_queue.get(timeout=0.1)
                calibration_samples.append(data)
                
                # Drain excess calibration data
                while self.audio_queue.qsize() > 10:
                    try:
                        self.audio_queue.get_nowait()
                    except queue.Empty:
                        break
                        
            except queue.Empty:
                pass
            
            time.sleep(0.05)
        
        # Analyze calibration data
        if calibration_samples:
            total_energy = 0
            sample_count = 0
            
            for sample in calibration_samples:
                audio_np = np.frombuffer(sample, dtype=np.int16)
                energy = np.sqrt(np.mean(audio_np.astype(np.float32) ** 2))
                total_energy += energy
                sample_count += 1
            
            avg_ambient_energy = total_energy / sample_count if sample_count > 0 else self.energy_threshold
            logging.info(f"Ambient energy level: {avg_ambient_energy:.2f}")
            
            # Update VAD thresholds based on calibration
            self.vad.ambient_energy = avg_ambient_energy
        
        logging.info("Environment calibration complete. Ready for recognition.")
    
    def listen_and_transcribe(self, silence_threshold: float = 2.8, phrase_timeout: float = 20.0,
                            calibration_duration: float = 3.0) -> Generator[Tuple[str, str, Dict[str, Any]], None, None]:
        """
        Enhanced transcription generator with advanced features.
        
        Yields:
            tuple: (result_type, text, metadata)
                result_type: 'partial', 'final', or 'error'
                text: transcribed text
                metadata: additional information (confidence, timing, etc.)
        """
        recognizer = vosk.KaldiRecognizer(self.model, self.samplerate)
        
        # Enhanced recognizer configuration
        if hasattr(recognizer, 'SetWords'):
            recognizer.SetWords(True)
        if hasattr(recognizer, 'SetPartialWords'):
            recognizer.SetPartialWords(True)
        
        self.is_listening = True
        retry_count = 0
        
        while retry_count <= self.max_retries:
            try:
                with sd.RawInputStream(
                    samplerate=self.samplerate,
                    blocksize=self.chunk_size,
                    device=self.device,
                    dtype='int16',
                    channels=1,
                    callback=self._audio_callback
                ):
                    
                    self._calibrate_environment(calibration_duration)
                    
                    # Speech detection state
                    is_speaking = False
                    speech_start_time = 0
                    last_speech_time = time.time()
                    phrase_start_time = time.time()
                    silence_start_time = 0
                    
                    # Audio buffering for padding
                    audio_buffer = deque(maxlen=int(self.speech_padding_before * self.samplerate / self.chunk_size))
                    
                    while self.is_listening:
                        try:
                            # Get audio data with timeout
                            data = self.audio_queue.get(timeout=0.1)
                            audio_buffer.append(data)
                            
                            # Voice activity detection
                            is_speech_detected = self.vad.is_speech(data)
                            current_time = time.time()
                            
                            # State transitions
                            if is_speech_detected:
                                if not is_speaking:
                                    # Start of new speech
                                    is_speaking = True
                                    speech_start_time = current_time
                                    phrase_start_time = current_time
                                    
                                    # Add buffered audio for padding
                                    for buffered_data in audio_buffer:
                                        if recognizer.AcceptWaveform(buffered_data):
                                            pass  # Intermediate result, ignore
                                
                                last_speech_time = current_time
                                silence_start_time = 0
                                
                                # Process current audio
                                if recognizer.AcceptWaveform(data):
                                    # Intermediate result available
                                    partial_result = json.loads(recognizer.PartialResult())
                                    if partial_result.get('partial'):
                                        yield self._create_partial_result(partial_result['partial'])
                            
                            else:  # No speech detected
                                if is_speaking:
                                    if silence_start_time == 0:
                                        silence_start_time = current_time
                                    
                                    # Continue processing audio during silence (for padding)
                                    if recognizer.AcceptWaveform(data):
                                        partial_result = json.loads(recognizer.PartialResult())
                                        if partial_result.get('partial'):
                                            yield self._create_partial_result(partial_result['partial'])
                            
                            # Check for end-of-speech conditions
                            if is_speaking:
                                silence_duration = current_time - silence_start_time if silence_start_time > 0 else 0
                                speech_duration = current_time - speech_start_time
                                total_phrase_duration = current_time - phrase_start_time
                                
                                # End speech if conditions are met
                                should_end = False
                                end_reason = ""
                                
                                if silence_duration > silence_threshold:
                                    should_end = True
                                    end_reason = "silence_threshold"
                                elif total_phrase_duration > phrase_timeout:
                                    should_end = True
                                    end_reason = "phrase_timeout"
                                elif speech_duration < self.min_speech_duration and silence_duration > 1.0:
                                    should_end = True
                                    end_reason = "min_speech_duration"
                                
                                if should_end:
                                    # Finalize the recognition
                                    final_result = self._finalize_recognition(recognizer, end_reason)
                                    if final_result:
                                        yield final_result
                                    
                                    # Reset state
                                    is_speaking = False
                                    silence_start_time = 0
                        
                        except queue.Empty:
                            # No audio data, check for timeouts
                            current_time = time.time()
                            if is_speaking:
                                total_phrase_duration = current_time - phrase_start_time
                                if total_phrase_duration > phrase_timeout:
                                    final_result = self._finalize_recognition(recognizer, "phrase_timeout")
                                    if final_result:
                                        yield final_result
                                    is_speaking = False
                        
                        except Exception as e:
                            logging.error(f"Audio processing error: {e}")
                            if self.enable_recovery_mode:
                                yield ("error", f"Audio processing error: {e}", {"recoverable": True})
                                time.sleep(0.1)  # Brief pause before continuing
                            else:
                                raise
                
                # If we get here without exception, break the retry loop
                break
                
            except Exception as e:
                retry_count += 1
                logging.error(f"Stream error (attempt {retry_count}/{self.max_retries + 1}): {e}")
                
                if retry_count <= self.max_retries and self.enable_recovery_mode:
                    logging.info(f"Attempting recovery in {self.retry_delay} seconds...")
                    time.sleep(self.retry_delay)
                    yield ("error", f"Stream error, attempting recovery (attempt {retry_count})", {"recoverable": True})
                else:
                    yield ("error", f"Failed to establish audio stream after {self.max_retries} attempts: {e}", {"recoverable": False})
                    break
        
        self.is_listening = False
        logging.info("Speech recognition stopped")
    
    def _create_partial_result(self, text: str) -> Tuple[str, str, Dict[str, Any]]:
        """Create a partial result with metadata."""
        processed_text = text
        if self.enable_custom_vocabulary or self.enable_grammar_correction:
            processed_text = self.text_processor.process_text(text)
        
        metadata = {
            "original_text": text,
            "timestamp": time.time(),
            "type": "partial"
        }
        
        return ("partial", processed_text, metadata)
    
    def _finalize_recognition(self, recognizer, end_reason: str) -> Optional[Tuple[str, str, Dict[str, Any]]]:
        """Finalize recognition and apply post-processing."""
        try:
            # Get final result from recognizer
            final_result_json = json.loads(recognizer.FinalResult())
            final_text = final_result_json.get('text', '').strip()
            confidence = final_result_json.get('confidence', 0.0)
            
            # Skip empty results
            if not final_text:
                return None
            
            # Apply confidence filtering
            if self.enable_confidence_filtering and confidence < self.min_confidence_threshold:
                logging.debug(f"Filtered low confidence result: {confidence:.2f} < {self.min_confidence_threshold}")
                return None
            
            # Process text
            original_text = final_text
            processed_text = final_text
            
            if self.enable_custom_vocabulary or self.enable_grammar_correction or self.enable_spell_check:
                processed_text = self.text_processor.process_text(final_text)
            
            # Update statistics
            self.stats['total_phrases'] += 1
            self.stats['successful_recognitions'] += 1
            self.stats['average_confidence'] = (
                (self.stats['average_confidence'] * (self.stats['successful_recognitions'] - 1) + confidence) /
                self.stats['successful_recognitions']
            )
            
            # Create metadata
            metadata = {
                "original_text": original_text,
                "confidence": confidence,
                "end_reason": end_reason,
                "timestamp": time.time(),
                "processing_applied": {
                    "vocabulary_correction": self.enable_custom_vocabulary,
                    "grammar_correction": self.enable_grammar_correction,
                    "spell_check": self.enable_spell_check
                },
                "type": "final"
            }
            
            # Add detailed logging if enabled
            if os.getenv("ENABLE_DETAILED_LOGGING", "true").lower() == "true":
                logging.info(f"Recognition completed - Confidence: {confidence:.2f}, End reason: {end_reason}")
                if original_text != processed_text:
                    logging.info(f"Text processing applied: '{original_text}' -> '{processed_text}'")
            
            return ("final", processed_text, metadata)
        
        except Exception as e:
            logging.error(f"Error finalizing recognition: {e}")
            self.stats['failed_recognitions'] += 1
            return None
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get recognition statistics."""
        return {
            **self.stats,
            "success_rate": (
                self.stats['successful_recognitions'] / max(1, self.stats['total_phrases']) * 100
            ),
            "is_listening": self.is_listening
        }
    
    def stop_listening(self):
        """Stop the recognition process."""
        self.is_listening = False
        logging.info("Stop signal sent to speech recognizer")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit with cleanup."""
        self.stop_listening()
        self.executor.shutdown(wait=True)
        if exc_type:
            logging.error(f"Exception in speech recognizer: {exc_type.__name__}: {exc_val}")
        return False
