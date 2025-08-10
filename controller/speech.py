import sys
import os
import time
import signal
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import json
from processor.speech_recognizer import EnhancedVoskSpeechRecognizer

class ColoredFormatter(logging.Formatter):
    """Custom formatter with colors for different log levels."""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        log_color = self.COLORS.get(record.levelname, self.RESET)
        record.levelname = f"{log_color}{record.levelname}{self.RESET}"
        return super().format(record)

class AdvancedStatusDisplay:
    """
    Enhanced status display with rich information and smooth animations.
    """
    def __init__(self):
        self._spinner_chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"  # Braille spinner
        self._spinner_index = 0
        
        # ANSI escape codes
        self.CLEAR_LINE = "\x1b[2K"
        self.CURSOR_TO_START = "\r"
        self.HIDE_CURSOR = "\x1b[?25l"
        self.SHOW_CURSOR = "\x1b[?25h"
        
        # Status tracking
        self.start_time = time.time()
        self.last_update = time.time()
        
        # Hide cursor for smoother animation
        sys.stdout.write(self.HIDE_CURSOR)
        sys.stdout.flush()
    
    def update_listening(self, partial_text: str = "", metadata: Optional[Dict[str, Any]] = None):
        """Update the listening status with partial text and metadata."""
        self._spinner_index = (self._spinner_index + 1) % len(self._spinner_chars)
        spinner = self._spinner_chars[self._spinner_index]
        
        # Calculate session time
        session_duration = time.time() - self.start_time
        duration_str = f"{int(session_duration // 60):02d}:{int(session_duration % 60):02d}"
        
        # Format the status line
        if partial_text:
            # Show partial text with visual emphasis
            status_line = f"🎤 {spinner} Listening [{duration_str}] ➤ {partial_text}"
            if len(status_line) > 100:  # Truncate if too long
                status_line = status_line[:97] + "..."
        else:
            status_line = f"🎤 {spinner} Listening [{duration_str}] ➤ Ready for speech..."
        
        # Add confidence if available
        if metadata and metadata.get('confidence'):
            confidence = metadata['confidence']
            if confidence > 0.8:
                conf_indicator = "🟢"
            elif confidence > 0.5:
                conf_indicator = "🟡"
            else:
                conf_indicator = "🔴"
            status_line += f" {conf_indicator}"
        
        # Update display
        sys.stdout.write(f"{self.CURSOR_TO_START}{self.CLEAR_LINE}{status_line}")
        sys.stdout.flush()
        self.last_update = time.time()
    
    def show_final_result(self, text: str, metadata: Optional[Dict[str, Any]] = None):
        """Display final recognition result with rich formatting."""
        # Clear the listening line
        sys.stdout.write(f"{self.CURSOR_TO_START}{self.CLEAR_LINE}")
        
        # Format timestamp
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Format the result with visual elements
        result_prefix = "✅"
        confidence_info = ""
        
        if metadata:
            confidence = metadata.get('confidence', 0)
            end_reason = metadata.get('end_reason', 'unknown')
            
            # Confidence indicator
            if confidence > 0.8:
                confidence_info = f"🟢 {confidence:.1%}"
            elif confidence > 0.5:
                confidence_info = f"🟡 {confidence:.1%}"
            else:
                confidence_info = f"🔴 {confidence:.1%}"
            
            # End reason indicator
            reason_indicators = {
                'silence_threshold': '⏸️',
                'phrase_timeout': '⏰',
                'min_speech_duration': '⚡'
            }
            reason_icon = reason_indicators.get(end_reason, '🔄')
            
            result_prefix = f"{result_prefix} {reason_icon}"
        
        # Format the complete result
        result_line = f"[{timestamp}] {result_prefix} {text}"
        if confidence_info:
            result_line += f" ({confidence_info})"
        
        # Print with color if text was processed
        if metadata and metadata.get('original_text') != text:
            original = metadata['original_text']
            print(f"\033[36m{result_line}\033[0m")  # Cyan for processed text
            print(f"\033[90m    Original: {original}\033[0m")  # Gray for original
        else:
            print(f"\033[32m{result_line}\033[0m")  # Green for normal text
        
        sys.stdout.flush()
    
    def show_error(self, error_msg: str, recoverable: bool = True):
        """Display error message with appropriate formatting."""
        sys.stdout.write(f"{self.CURSOR_TO_START}{self.CLEAR_LINE}")
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        error_icon = "⚠️" if recoverable else "❌"
        
        error_line = f"[{timestamp}] {error_icon} {error_msg}"
        print(f"\033[31m{error_line}\033[0m")  # Red for errors
        sys.stdout.flush()
    
    def show_info(self, message: str):
        """Display informational message."""
        sys.stdout.write(f"{self.CURSOR_TO_START}{self.CLEAR_LINE}")
        
        timestamp = datetime.now().strftime('%H:%M:%S')
        info_line = f"[{timestamp}] ℹ️  {message}"
        print(f"\033[34m{info_line}\033[0m")  # Blue for info
        sys.stdout.flush()
    
    def show_ready(self):
        """Show initial ready state."""
        self.update_listening()
    
    def cleanup(self):
        """Clean up the display."""
        sys.stdout.write(f"{self.CURSOR_TO_START}{self.CLEAR_LINE}{self.SHOW_CURSOR}")
        sys.stdout.flush()

class SpeechRecognitionController:
    """
    Advanced speech recognition controller with comprehensive error handling
    and rich user experience.
    """
    
    def __init__(self):
        self.recognizer: Optional[EnhancedVoskSpeechRecognizer] = None
        self.status_display: Optional[AdvancedStatusDisplay] = None
        self.session_stats = {
            'session_start': time.time(),
            'total_phrases': 0,
            'successful_recognitions': 0,
            'errors': 0
        }
        
        # Configuration
        self._load_config()
        self._setup_logging()
        self._setup_signal_handlers()
        
        # Create necessary directories
        os.makedirs(os.path.dirname(self.log_file), exist_ok=True)
        os.makedirs(os.path.dirname(self.custom_vocabulary_path), exist_ok=True)
        
    def _load_config(self):
        """Load configuration from environment variables with validation."""
        self.model_dir = os.getenv("VOSK_MODEL_PATH")
        if not self.model_dir:
            raise ValueError("VOSK_MODEL_PATH is not set in the .env file")
        
        self.log_file = "logs/speech_log.txt"
        self.detailed_log_file = "logs/detailed_speech_log.json"
        
        # Audio settings
        self.sample_rate = int(os.getenv("RECOGNIZER_SAMPLE_RATE", 16000))
        self.calibration_duration = float(os.getenv("NOISE_CALIBRATION_DURATION", 3.0))
        self.silence_threshold = float(os.getenv("SILENCE_THRESHOLD", 2.8))
        self.phrase_timeout = float(os.getenv("PHRASE_TIMEOUT", 20.0))
        
        # Advanced settings
        self.enable_detailed_logging = os.getenv("ENABLE_DETAILED_LOGGING", "true").lower() == "true"
        self.enable_audio_stats = os.getenv("LOG_AUDIO_STATS", "true").lower() == "true"
        self.custom_vocabulary_path = os.getenv("CUSTOM_VOCABULARY_PATH", "config/custom_vocabulary.json")
        
        # Create custom vocabulary file if it doesn't exist
        self._ensure_custom_vocabulary_exists()
    
    def _ensure_custom_vocabulary_exists(self):
        """Ensure custom vocabulary file exists with default content."""
        if not os.path.exists(self.custom_vocabulary_path):
            # Create default vocabulary from environment variables
            priority_names = os.getenv("PRIORITY_NAMES", "Quip,Oracle,Byte,Mika,Kira").split(",")
            technical_terms = os.getenv("TECHNICAL_TERMS", "API,database,server").split(",")
            
            default_vocab = {
                "priority_names": {},
                "technical_terms": {},
                "common_corrections": {
                    "artifical": "artificial",
                    "intelligance": "intelligence",
                    "recieve": "receive",
                    "seperate": "separate",
                    "definitly": "definitely"
                }
            }
            
            # Add priority names with common mispronunciations
            for name in priority_names:
                name = name.strip()
                if name:
                    default_vocab["priority_names"][name.lower()] = name
                    # Add common variations
                    if name.lower() == "quip":
                        default_vocab["priority_names"]["kwip"] = name
                        default_vocab["priority_names"]["kip"] = name
                    elif name.lower() == "oracle":
                        default_vocab["priority_names"]["orical"] = name
                        default_vocab["priority_names"]["oracal"] = name
            
            # Add technical terms
            for term in technical_terms:
                term = term.strip()
                if term:
                    default_vocab["technical_terms"][term.lower()] = term
            
            # Write to file
            os.makedirs(os.path.dirname(self.custom_vocabulary_path), exist_ok=True)
            with open(self.custom_vocabulary_path, 'w', encoding='utf-8') as f:
                json.dump(default_vocab, f, indent=2, ensure_ascii=False)
            
            print(f"Created default custom vocabulary at: {self.custom_vocabulary_path}")
    
    def _setup_logging(self):
        """Setup comprehensive logging."""
        log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper())
        
        # Create formatters
        console_formatter = ColoredFormatter(
            '%(levelname)s - %(message)s'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Setup root logger
        root_logger = logging.getLogger()
        root_logger.setLevel(log_level)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(log_level)
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)
        
        # File handler
        os.makedirs('logs', exist_ok=True)
        file_handler = logging.FileHandler('logs/speech_recognition.log', mode='a')
        file_handler.setLevel(log_level)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            print(f"\n🛑 Received signal {signum}, shutting down gracefully...")
            self._shutdown_gracefully()
            sys.exit(0)
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def _shutdown_gracefully(self):
        """Perform graceful shutdown."""
        if self.recognizer:
            self.recognizer.stop_listening()
        
        if self.status_display:
            self.status_display.cleanup()
        
        # Print session statistics
        session_duration = time.time() - self.session_stats['session_start']
        print(f"\n📊 Session Statistics:")
        print(f"   Duration: {session_duration:.1f} seconds")
        print(f"   Total phrases: {self.session_stats['total_phrases']}")
        print(f"   Successful recognitions: {self.session_stats['successful_recognitions']}")
        print(f"   Errors: {self.session_stats['errors']}")
        
        if self.session_stats['total_phrases'] > 0:
            success_rate = (self.session_stats['successful_recognitions'] / 
                          self.session_stats['total_phrases']) * 100
            print(f"   Success rate: {success_rate:.1f}%")
    
    def _log_detailed_result(self, result_type: str, text: str, metadata: Dict[str, Any]):
        """Log detailed results to JSON file for analysis."""
        if not self.enable_detailed_logging:
            return
        
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "type": result_type,
            "text": text,
            "metadata": metadata,
            "session_id": id(self)  # Simple session identifier
        }
        
        try:
            # Append to JSON log file
            with open(self.detailed_log_file, 'a', encoding='utf-8') as f:
                json.dump(log_entry, f, ensure_ascii=False)
                f.write('\n')
        except Exception as e:
            logging.debug(f"Failed to write detailed log: {e}")
    
    def start_listening(self):
        """
        Main method to start the enhanced speech recognition system.
        """
        if not os.path.exists(self.model_dir):
            print(f"❌ Error: Model directory not found at '{self.model_dir}'")
            print("💡 Please run the 'run.sh' script to download the required model.")
            sys.exit(1)
        
        print("🎙️  Enhanced Speech Recognition System")
        print("=" * 50)
        print(f"Model: {self.model_dir}")
        print(f"Sample Rate: {self.sample_rate} Hz")
        print(f"Silence Threshold: {self.silence_threshold}s")
        print(f"Phrase Timeout: {self.phrase_timeout}s")
        print(f"Calibration Duration: {self.calibration_duration}s")
        print(f"Custom Vocabulary: {'✅' if os.path.exists(self.custom_vocabulary_path) else '❌'}")
        print(f"Log File: {self.log_file}")
        print("=" * 50)
        print("Press Ctrl+C to stop the system")
        print()
        
        try:
            # Initialize recognizer
            self.recognizer = EnhancedVoskSpeechRecognizer(
                model_path=self.model_dir,
                samplerate=self.sample_rate
            )
            
            self.status_display = AdvancedStatusDisplay()
            
            logging.info("🚀 Speech recognition system started")
            
            # Start the recognition loop
            transcription_generator = self.recognizer.listen_and_transcribe(
                silence_threshold=self.silence_threshold,
                phrase_timeout=self.phrase_timeout,
                calibration_duration=self.calibration_duration
            )
            
            self.status_display.show_ready()
            
            # Process results
            for result_type, text, metadata in transcription_generator:
                if result_type == "partial":
                    self.status_display.update_listening(text, metadata)
                    
                elif result_type == "final" and text.strip():
                    self._handle_final_result(text, metadata)
                    
                elif result_type == "error":
                    self._handle_error(text, metadata)
            
        except KeyboardInterrupt:
            print("\n🛑 Stopping speech recognition...")
            
        except FileNotFoundError as e:
            print(f"❌ File not found: {e}")
            print("💡 Please check your model path and run the setup script.")
            
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            logging.error(f"Unexpected error in speech controller: {e}", exc_info=True)
            
        finally:
            self._shutdown_gracefully()
    
    def _handle_final_result(self, text: str, metadata: Dict[str, Any]):
        """Handle final recognition results."""
        self.session_stats['total_phrases'] += 1
        self.session_stats['successful_recognitions'] += 1
        
        # Display the result
        self.status_display.show_final_result(text, metadata)
        
        # Log to file
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        confidence = metadata.get('confidence', 0)
        log_message = f"[{timestamp}] ✅ {text} (confidence: {confidence:.1%})"
        
        with open(self.log_file, "a", encoding='utf-8') as log_file:
            log_file.write(log_message + "\n")
        
        # Log detailed information
        self._log_detailed_result("final", text, metadata)
        
        # Show ready for next input
        self.status_display.show_ready()
    
    def _handle_error(self, error_msg: str, metadata: Dict[str, Any]):
        """Handle recognition errors."""
        self.session_stats['errors'] += 1
        recoverable = metadata.get('recoverable', False)
        
        self.status_display.show_error(error_msg, recoverable)
        
        # Log error
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_message = f"[{timestamp}] ❌ ERROR: {error_msg}"
        
        with open(self.log_file, "a", encoding='utf-8') as log_file:
            log_file.write(log_message + "\n")
        
        self._log_detailed_result("error", error_msg, metadata)
        
        if recoverable:
            self.status_display.show_ready()
        else:
            self.status_display.cleanup()
            sys.exit(1)