#!/bin/bash

# --- Helper Functions ---
echo_info() {
    # Blue color for informational messages
    echo -e "\e[34m[INFO]\e[0m $1"
}

echo_error() {
    # Red color for error messages
    echo -e "\e[31m[ERROR]\e[0m $1" >&2
}

echo_success() {
    # Green color for success messages
    echo -e "\e[32m[SUCCESS]\e[0m $1"
}

# --- Load Environment Variables ---
# Check for the tuner.conf file and load its variables. This is crucial for configuration.
if [ -f tuner.conf ]; then
    echo_info "Loading environment variables from tuner.conf file..."
    # Export the variables from tuner.conf to be available to this script
    export $(cat tuner.conf | sed 's/#.*//g' | xargs)
else
    echo_error "tuner.conf file not found. Please create one with VOSK_MODEL_PATH and VOSK_MODEL_URL."
    exit 1
fi

# --- Configuration (from tuner.conf) ---
PYTHON_CMD="python3"
VENV_DIR="venv"
PYTHON_SCRIPT="main.py"

# Model configuration is now dynamically set from the loaded environment variables
MODEL_DIR=${VOSK_MODEL_PATH}
MODEL_URL=${VOSK_MODEL_URL}
MODEL_ZIP_FILE=$(basename "$MODEL_URL")
# The name of the folder inside the zip file (e.g., "vosk-model-en-in-0.5")
MODEL_UNZIPPED_NAME="${MODEL_ZIP_FILE%.zip}"

# TTS configuration
TTS_CACHE_DIR=${TTS_MODEL_CACHE_DIR:-"models/tts_cache"}

if [ "$1" == "1" ]; then
    echo_info "Running in FULL SETUP mode..."
    # 1. Check if Python 3 is installed
    if ! command -v $PYTHON_CMD &> /dev/null; then
        echo_error "Python 3 is not installed. Please install it to continue."
        echo_info "On Debian/Ubuntu: sudo apt-get install python3 python3-pip python3-venv"
        echo_info "On macOS (using Homebrew): brew install python"
        exit 1
    fi
    echo_success "Python 3 is installed."

    # 2. Check for and create the virtual environment if it doesn't exist
    if [ ! -d "$VENV_DIR" ]; then
        echo_info "Creating Python virtual environment in '$VENV_DIR'..."
        $PYTHON_CMD -m venv $VENV_DIR
        if [ $? -ne 0 ]; then
            echo_error "Failed to create virtual environment."
            exit 1
        fi
    else
        echo_success "Virtual environment already exists."
    fi

    # 3. Activate the virtual environment and install dependencies
    source "$VENV_DIR/bin/activate"
    echo_success "Virtual environment activated."

    echo_info "Upgrading pip to the latest version..."
    pip install --upgrade pip > /dev/null

    echo_info "Installing core required packages from requirements.txt..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo_error "Failed to install dependencies from requirements.txt."
        deactivate
        exit 1
    fi

    # 4. Install TTS and audio processing dependencies
    echo_info "Installing TTS and audio processing dependencies..."

    # Check Python version for compatibility
    PYTHON_VERSION=$($PYTHON_CMD -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    echo_info "Detected Python version: $PYTHON_VERSION"

    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo_info "Detected macOS. Ensuring compatibility..."
        # Install specific versions that work well on macOS
        pip install --upgrade torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
        if [ $? -ne 0 ]; then
            echo_info "PyTorch installation had issues, but continuing..."
        fi
    fi

    # Install fallback TTS engines first (more compatible)
    echo_info "Installing fallback TTS engines..."
    pip install pyttsx3>=2.90 gTTS>=2.3.0 pygame>=2.1.0
    if [ $? -ne 0 ]; then
        echo_info "Some fallback TTS engines failed to install, but continuing..."
    fi

    # Try to install Coqui TTS (may fail on older Python versions)
    echo_info "Attempting to install Coqui TTS..."
    if python -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)" 2>/dev/null; then
        # Python 3.10+ - safe to install full TTS
        pip install "TTS>=0.22.0,<0.23.0"
        if [ $? -eq 0 ]; then
            echo_success "Coqui TTS installed successfully."
        else
            echo_info "Coqui TTS installation failed, but fallback engines are available."
        fi
    else
        # Python < 3.10 - use older TTS version or skip
        echo_info "Python version < 3.10 detected. Trying compatible TTS version..."
        pip install "TTS>=0.13.0,<0.20.0" 2>/dev/null || echo_info "Coqui TTS not compatible, using fallback engines only."
    fi

    # Install audio processing libraries
    pip install "librosa>=0.10.0" "soundfile>=0.12.0" "numpy>=1.21.0"
    if [ $? -ne 0 ]; then
        echo_error "Failed to install audio processing dependencies."
        deactivate
        exit 1
    fi

    # 5. Check for system-level audio dependencies
    echo_info "Checking system audio dependencies..."
    if command -v apt-get &> /dev/null; then
        echo_info "Detected Debian/Ubuntu system."
        echo_info "If you encounter audio issues, install: sudo apt-get install libsndfile1 ffmpeg portaudio19-dev"
    elif command -v brew &> /dev/null; then
        echo_info "Detected macOS with Homebrew."
        echo_info "If you encounter audio issues, install: brew install libsndfile ffmpeg portaudio"
    elif command -v pacman &> /dev/null; then
        echo_info "Detected Arch Linux."
        echo_info "If you encounter audio issues, install: sudo pacman -S libsndfile ffmpeg portaudio"
    fi

    echo_success "All dependencies installed successfully."

    # 6. Create TTS cache directory
    mkdir -p "$TTS_CACHE_DIR"
    echo_success "TTS cache directory created at '$TTS_CACHE_DIR'."

    # 7. Check for and download the Vosk model if it doesn't exist
    if [ ! -d "$MODEL_DIR" ]; then
        echo_info "Vosk model not found at '$MODEL_DIR'. Attempting to download..."

        # Create models directory if it doesn't exist
        mkdir -p models

        # Check for required commands
        if ! command -v wget &> /dev/null || ! command -v unzip &> /dev/null; then
            echo_error "'wget' and 'unzip' are required. Please install them."
            echo_info "On Debian/Ubuntu: sudo apt-get install wget unzip"
            echo_info "On macOS (using Homebrew): brew install wget"
            deactivate
            exit 1
        fi

        # Download to models directory
        echo_info "Downloading Vosk model from $MODEL_URL..."
        wget -q --show-progress -P models/ "$MODEL_URL"
        if [ $? -ne 0 ]; then
            echo_error "Failed to download the Vosk model."
            deactivate
            exit 1
        fi

        # Unzip in models directory
        echo_info "Unzipping Vosk model..."
        unzip -q "models/$MODEL_ZIP_FILE" -d "models/"
        if [ $? -ne 0 ]; then
            echo_error "Failed to unzip the Vosk model."
            rm "models/$MODEL_ZIP_FILE" # Clean up failed download
            deactivate
            exit 1
        fi

        # Clean up the zip file
        rm "models/$MODEL_ZIP_FILE"
        echo_success "Vosk model downloaded and unpacked successfully in 'models/'."
    fi
else
    echo_info "Running in FAST mode. To run full setup, use: ./run.sh 1"
    if [ ! -d "$VENV_DIR" ]; then
        echo_error "Virtual environment '$VENV_DIR' not found. Please run full setup first: ./run.sh 1"
        exit 1
    fi
    source "$VENV_DIR/bin/activate"
    echo_success "Virtual environment activated."
fi

# Final check for the model directory
if [ ! -d "$MODEL_DIR" ]; then
    echo_error "Vosk model directory '$MODEL_DIR' still not found after download attempt."
    deactivate
    exit 1
fi
echo_success "Vosk model found at '$MODEL_DIR'."

if [ "$1" == "1" ]; then
    # 8. Pre-download TTS models to avoid delays during first run
    echo_info "Testing TTS availability..."
    python3 -c "
import os
os.environ['TTS_CACHE'] = '$TTS_CACHE_DIR'
tts_available = False

# Test Coqui TTS
try:
    from TTS.api import TTS
    print('[INFO] Coqui TTS is available. Downloading default model...')
    tts = TTS(model_name='tts_models/en/ljspeech/tacotron2-DDC', progress_bar=True, gpu=False)
    print('[SUCCESS] Coqui TTS model pre-downloaded successfully.')
    tts_available = True
except Exception as e:
    print(f'[INFO] Coqui TTS not available: {e}')

# Test pyttsx3
if not tts_available:
    try:
        import pyttsx3
        engine = pyttsx3.init()
        if engine:
            print('[SUCCESS] pyttsx3 TTS engine is available as fallback.')
            tts_available = True
    except Exception as e:
        print(f'[INFO] pyttsx3 not available: {e}')

# Test gTTS
if not tts_available:
    try:
        from gtts import gTTS
        print('[SUCCESS] gTTS is available as fallback.')
        tts_available = True
    except Exception as e:
        print(f'[INFO] gTTS not available: {e}')

if not tts_available:
    print('[WARNING] No TTS engines available. Voice synthesis will be simulated.')
else:
    print('[SUCCESS] At least one TTS engine is available.')
" 2>/dev/null || echo_info "TTS availability will be checked at runtime."
fi

# 9. Display system information
echo_info "=== SYNDICATE VOICE SYSTEM READY ==="
echo_info "Speech Recognition Model: $MODEL_DIR"
echo_info "TTS Cache Directory: $TTS_CACHE_DIR"
echo_info "TTS Enabled: ${TTS_ENABLED:-true}"
echo_info "Personality Introductions: ${TTS_INTRODUCTION_ENABLED:-true}"
echo_info "======================================"

# 10. Run the main Python script
echo_info "Starting the Syndicate Voice System..."
echo_info "Press Ctrl+C to stop the application."
$PYTHON_CMD -u $PYTHON_SCRIPT # -u for unbuffered output

# Deactivate the virtual environment upon exiting the script
deactivate
echo_success "Virtual environment deactivated. Syndicate shutdown complete."