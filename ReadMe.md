# 🎤 Enhanced Speech Recognition System v2.0

A comprehensive, production-ready voice-to-text system with advanced features for accurate speech recognition, custom vocabulary support, and robust error handling.

## ✨ Features

### 🎯 Core Capabilities
- **High-Accuracy Recognition**: Uses Vosk ASR with optimized settings for maximum accuracy
- **Real-Time Processing**: Live transcription with minimal latency
- **Custom Vocabulary**: Configurable vocabulary for names, technical terms, and domain-specific language
- **Grammar Correction**: Automatic grammar and spelling correction
- **Advanced Audio Processing**: Noise suppression, echo cancellation, and voice activity detection

### 🔧 Advanced Features
- **Dynamic Thresholding**: Adaptive silence detection based on ambient noise
- **Multi-threaded Processing**: Optimized performance with concurrent processing
- **Comprehensive Logging**: Detailed logs for debugging and analysis
- **Error Recovery**: Robust error handling with automatic recovery
- **Rich User Interface**: Real-time feedback with visual indicators
- **Session Statistics**: Track recognition accuracy and performance metrics

### 🎛️ Configurable Settings
- **Audio Processing**: Sample rates, chunk sizes, VAD aggressiveness
- **Speech Detection**: Silence thresholds, phrase timeouts, speech padding
- **Text Processing**: Grammar correction, spell checking, text normalization
- **Performance**: Threading, buffering, and optimization settings

## 📋 Requirements

### System Requirements
- **Python**: 3.7 or higher
- **Operating System**: Linux, macOS, or Windows
- **Memory**: Minimum 2GB RAM (4GB recommended)
- **Audio**: Working microphone/audio input device

### Dependencies
- `vosk` - Speech recognition engine
- `sounddevice` - Audio input/output
- `webrtcvad-wheels` - Voice activity detection
- `numpy` - Numerical computing
- `python-dotenv` - Environment variable management
- Additional packages listed in `requirements.txt`

## 🚀 Quick Start

### 1. Clone and Setup
```bash
# Clone the repository
git clone <repository-url>
cd enhanced-speech-recognition

# Run the setup script (handles everything automatically)
./run.sh
```

### 2. Manual Setup (if needed)
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Download Vosk model (if not auto-downloaded)
wget https://alphacephei.com/vosk/models/vosk-model-en-in-0.5.zip
unzip vosk-model-en-in-0.5.zip -d models/

# Run the application
python3 main.py
```

## ⚙️ Configuration

### Environment Variables (.env)

The system is highly configurable through the `.env` file. Here are the key settings:

#### Core Audio Settings
```bash
# Model configuration
VOSK_MODEL_PATH="models/vosk-model-en-in-0.5"
VOSK_MODEL_URL="https://alphacephei.com/vosk/models/vosk-model-en-in-0.5.zip"

# Audio processing
RECOGNIZER_SAMPLE_RATE=16000
NOISE_CALIBRATION_DURATION=3.0
VAD_AGGRESSIVENESS=2              # 0-3, higher = more aggressive
SILENCE_THRESHOLD=2.8             # Seconds of silence to end phrase
PHRASE_TIMEOUT=20.0               # Maximum phrase duration
```

#### Advanced Audio Processing
```bash
# Dynamic thresholds
DYNAMIC_ENERGY_THRESHOLD=true
DYNAMIC_ENERGY_ADJUSTMENT_DAMPING=0.15
DYNAMIC_ENERGY_RATIO=1.5

# Speech detection
MIN_SPEECH_DURATION=0.3
MAX_SILENCE_IN_SPEECH=0.8
SPEECH_PADDING_BEFORE=0.2
SPEECH_PADDING_AFTER=0.2
```

#### Text Processing
```bash
# Enhancement features
ENABLE_GRAMMAR_CORRECTION=true
ENABLE_SPELL_CHECK=true
ENABLE_CUSTOM_VOCABULARY=true
ENABLE_TEXT_NORMALIZATION=true

# Custom vocabulary
CUSTOM_VOCABULARY_PATH="config/custom_vocabulary.json"
PRIORITY_NAMES=Quip,Oracle,Byte,Mika,Kira
TECHNICAL_TERMS=API,database,server,client
```

#### Performance Optimization
```bash
# Threading and buffering
NUM_WORKER_THREADS=2
AUDIO_BUFFER_SIZE=50
ENABLE_MULTIPROCESSING=false
REALTIME_PROCESSING=true

# Error handling
ENABLE_RECOVERY_MODE=true
MAX_RETRIES=3
RETRY_DELAY=1.0
```

### Custom Vocabulary

Create or edit `config/custom_vocabulary.json`:

```json
{
  "priority_names": {
    "quip": "Quip",
    "kwip": "Quip",
    "oracle": "Oracle",
    "orical": "Oracle"
  },
  "technical_terms": {
    "api": "API",
    "database": "database"
  },
  "common_corrections": {
    "artifical": "artificial",
    "intelligance": "intelligence"
  }
}
```

## 🎮 Usage

### Starting the System
```bash
# Standard startup
./run.sh

# Setup only (don't start recognition)
./run.sh --setup-only

# Skip model download
./run.sh --skip-model

# Enable debug output
./run.sh --debug

# Run system tests
./run.sh --test-only
```

### Using the Interface

1. **Startup**: The system will calibrate for 3 seconds (remain quiet)
2. **Speaking**: Start speaking - you'll see partial transcription in real-time
3. **Results**: Final results appear after silence threshold is reached
4. **Visual Indicators**: 
   - 🎤 Listening indicator with session timer
   - ✅ Successful recognition
   - 🟢🟡🔴 Confidence indicators
   - ⚠️ Warnings and errors

### Keyboard Controls
- `Ctrl+C`: Gracefully stop the system
- The system handles interruption and cleanup automatically

## 📊 Monitoring and Logs

### Log Files
- `logs/speech_log.txt`: Human-readable transcription log
- `logs/speech_recognition.log`: System and error logs  
- `logs/detailed_speech_log.json`: Detailed JSON logs for analysis

### Real-time Statistics
The system displays:
- Session duration
- Total phrases processed
- Success rate
- Average confidence scores
- Error counts

### Performance Monitoring
```bash
# View real-time logs
tail -f logs/speech_recognition.log

# Analyze detailed logs
python3 -c "
import json
with open('logs/detailed_speech_log.json') as f:
    for line in f:
        data = json.loads(line)
        print(f'{data[\"timestamp\"]}: {data[\"text\"]} ({data[\"metadata\"].get(\"confidence\", 0):.1%})')
"
```

## 🔧 Advanced Configuration

### Model Selection
The system supports different Vosk models:

```bash
# English (US) - High accuracy, large size
VOSK_MODEL_PATH="models/vosk-model-en-us-0.22"
VOSK_MODEL_URL="https://alphacephei.com/vosk/models/vosk-model-en-us-0.22.zip"

# English (Indian) - Good for Indian accents
VOSK_MODEL_PATH="models/vosk-model-en-in-0.5"
VOSK_MODEL_URL="https://alphacephei.com/vosk/models/vosk-model-en-in-0.5.zip"

# Small English model - Faster, less accurate
VOSK_MODEL_PATH="models/vosk-model-small-en-us-0.15"
VOSK_MODEL_URL="https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
```

### Audio Device Selection
```bash
# List available audio devices
python3 -c "import sounddevice as sd; print(sd.query_devices())"

# Set specific device in code (processor/enhanced_speech_recognizer.py)
recognizer = EnhancedVoskSpeechRecognizer(
    model_path=model_dir,
    samplerate=sample_rate,
    device=device_id  # Specify device ID
)
```

### Fine-tuning Recognition

#### For Quiet Environments
```bash
VAD_AGGRESSIVENESS=0
ENERGY_THRESHOLD=300
SILENCE_THRESHOLD=2.0
```

#### For Noisy Environments  
```bash
VAD_AGGRESSIVENESS=3
ENERGY_THRESHOLD=1200
SILENCE_THRESHOLD=3.5
ENABLE_NOISE_SUPPRESSION=true
NOISE_SUPPRESSION_LEVEL=0.5
```

#### For Fast Speech
```bash
SILENCE_THRESHOLD=1.5
PHRASE_TIMEOUT=30.0
MIN_SPEECH_DURATION=0.1
```

#### For Conversational Speech
```bash
SILENCE_THRESHOLD=3.0
MAX_SILENCE_IN_SPEECH=1.2
SPEECH_PADDING_BEFORE=0.3
SPEECH_PADDING_AFTER=0.3
```

## 🧪 Testing and Development

### Running Tests
```bash
# Full system test
./run.sh --test-only

# Manual testing
python3 tests/system_test.py

# Test specific components
python3 -c "
from processor.enhanced_speech_recognizer import EnhancedVoskSpeechRecognizer
print('✅ Speech recognizer import successful')
"
```

### Development Mode
```bash
# Enable debug logging
export DEBUG=true
LOG_LEVEL=DEBUG ./run.sh

# Force complete reinstall
./run.sh --force-reinstall
```

## 🐛 Troubleshooting

### Common Issues

#### "No input audio devices found"
```bash
# Check audio devices
python3 -c "import sounddevice as sd; print(sd.query_devices())"

# On Linux, ensure user is in audio group
sudo usermod -a -G audio $USER
# Logout and login again
```

#### "Model directory not found"
```bash
# Redownload model
rm -rf models/
./run.sh --setup-only
```

#### "Package installation failed"
```bash
# Update pip and try again
pip install --upgrade pip setuptools wheel
./run.sh --force-reinstall
```

#### High CPU usage
```bash
# Reduce processing intensity
NUM_WORKER_THREADS=1
AUDIO_BUFFER_SIZE=25
ENABLE_NOISE_SUPPRESSION=false
```

#### Poor recognition accuracy
```bash
# Try larger model
VOSK_MODEL_PATH="models/vosk-model-en-us-0.22"

# Adjust for your environment
VAD_AGGRESSIVENESS=1  # Reduce if too aggressive
SILENCE_THRESHOLD=3.0  # Increase for natural speech
```

### Debug Mode
```bash
# Enable comprehensive debugging
DEBUG=true LOG_LEVEL=DEBUG ./run.sh --debug
```

### Performance Optimization
```bash
# Monitor system resources
htop

# Check audio latency
python3 -c "
import sounddevice as sd
print('Audio latency:', sd.query_devices()[sd.default.device]['default_low_input_latency'])
"
```

## 📁 Project Structure

```
enhanced-speech-recognition/
├── main.py                          # Main entry point
├── run.sh                          # Setup and run script
├── requirements.txt                # Python dependencies
├── .env                           # Configuration file
├── .gitignore                     # Git ignore rules
├── README.md                      # This file
├── controller/
│   ├── __init__.py
│   └── enhanced_speech_controller.py  # Main controller
├── processor/
│   ├── __init__.py
│   └── enhanced_speech_recognizer.py  # Core recognition engine
├── config/
│   └── custom_vocabulary.json     # Custom vocabulary
├── logs/
│   ├── speech_log.txt            # Transcription log
│   ├── speech_recognition.log    # System log
│   └── detailed_speech_log.json  # Detailed JSON log
├── models/
│   └── vosk-model-*/             # Vosk models
└── tests/
    └── system_test.py            # System tests
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes
4. Add tests if applicable
5. Ensure all tests pass: `./run.sh --test-only`
6. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- [Vosk Speech Recognition Toolkit](https://alphacephei.com/vosk/)
- [WebRTC Voice Activity Detection](https://webrtc.org/)
- [SoundDevice Python Library](https://python-sounddevice.readthedocs.io/)

## 📞 Support

For issues and questions:
1. Check the troubleshooting section above
2. Review the logs in `logs/` directory  
3. Run system tests with `./run.sh --test-only`
4. Open an issue with detailed information about your environment

---

**Happy speech recognition! 🎤✨**