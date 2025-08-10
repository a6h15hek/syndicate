#!/bin/bash

# Enhanced Speech Recognition System - Setup and Run Script
# This script handles complete system setup, dependency installation,
# model downloading, and system startup with comprehensive error handling.

set -euo pipefail  # Exit on any error, undefined variable, or pipe failure

# --- Color Output Functions ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Enhanced logging functions with emojis and colors
echo_info() {
    echo -e "${BLUE}ℹ️  [INFO]${NC} $1"
}

echo_success() {
    echo -e "${GREEN}✅ [SUCCESS]${NC} $1"
}

echo_warning() {
    echo -e "${YELLOW}⚠️  [WARNING]${NC} $1"
}

echo_error() {
    echo -e "${RED}❌ [ERROR]${NC} $1" >&2
}

echo_step() {
    echo -e "${CYAN}🔄 [STEP]${NC} $1"
}

echo_debug() {
    if [[ "${DEBUG:-}" == "true" ]]; then
        echo -e "${PURPLE}🐛 [DEBUG]${NC} $1"
    fi
}

# --- Utility Functions ---
check_command() {
    if command -v "$1" &> /dev/null; then
        return 0
    else
        return 1
    fi
}

get_os_info() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        echo "linux"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        echo "macos"
    elif [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "cygwin" ]]; then
        echo "windows"
    else
        echo "unknown"
    fi
}

check_system_requirements() {
    echo_step "Checking system requirements..."
    
    local os_type=$(get_os_info)
    echo_debug "Detected OS: $os_type"
    
    # Check for required system commands
    local required_commands=("python3" "pip3")
    local optional_commands=("wget" "curl" "unzip")
    
    for cmd in "${required_commands[@]}"; do
        if ! check_command "$cmd"; then
            echo_error "$cmd is required but not found"
            case $os_type in
                "linux")
                    echo_info "Install with: sudo apt-get install python3 python3-pip python3-venv"
                    ;;
                "macos")
                    echo_info "Install with: brew install python"
                    ;;
                *)
                    echo_info "Please install Python 3.7+ and pip"
                    ;;
            esac
            return 1
        fi
    done
    
    # Check Python version
    local python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    local min_version="3.7"
    
    if ! python3 -c "import sys; exit(0 if sys.version_info >= (3,7) else 1)" 2>/dev/null; then
        echo_error "Python $min_version or higher is required (found $python_version)"
        return 1
    fi
    
    echo_success "Python $python_version detected"
    
    # Check for download tools
    local download_cmd=""
    local unzip_available=""
    for cmd in "${optional_commands[@]}"; do
        if check_command "$cmd"; then
            case $cmd in
                "wget") download_cmd="wget" ;;
                "curl") download_cmd="curl" ;;
                "unzip") unzip_available="true" ;;
            esac
        fi
    done
    
    if [[ -z "$download_cmd" ]]; then
        echo_error "Either wget or curl is required for downloading models"
        case $os_type in
            "linux")
                echo_info "Install with: sudo apt-get install wget unzip"
                ;;
            "macos")
                echo_info "Install with: brew install wget"
                ;;
        esac
        return 1
    fi
    
    if [[ "${unzip_available:-}" != "true" ]]; then
        echo_error "unzip is required for extracting model files"
        return 1
    fi
    
    echo_success "System requirements check passed"
    return 0
}

# --- Environment Setup ---
load_environment() {
    echo_step "Loading environment configuration..."
    
    if [[ ! -f .env ]]; then
        echo_error ".env file not found"
        echo_info "Creating default .env file from template..."
        
        # Create a comprehensive default .env file
        cat > .env << 'EOF'
# ===== VOSK MODEL CONFIGURATION =====
VOSK_MODEL_PATH="models/vosk-model-en-in-0.5"
VOSK_MODEL_URL="https://alphacephei.com/vosk/models/vosk-model-en-in-0.5.zip"

# ===== CORE AUDIO SETTINGS =====
RECOGNIZER_SAMPLE_RATE=16000
NOISE_CALIBRATION_DURATION=3.0
VAD_AGGRESSIVENESS=2
SILENCE_THRESHOLD=2.8
PHRASE_TIMEOUT=20.0

# ===== ADVANCED AUDIO PROCESSING =====
AUDIO_CHUNK_SIZE=480
ENERGY_THRESHOLD=800
DYNAMIC_ENERGY_THRESHOLD=true
DYNAMIC_ENERGY_ADJUSTMENT_DAMPING=0.15
DYNAMIC_ENERGY_RATIO=1.5

# ===== SPEECH DETECTION =====
MIN_SPEECH_DURATION=0.3
MAX_SILENCE_IN_SPEECH=0.8
SPEECH_PADDING_BEFORE=0.2
SPEECH_PADDING_AFTER=0.2

# ===== TEXT PROCESSING =====
ENABLE_GRAMMAR_CORRECTION=true
ENABLE_SPELL_CHECK=true
ENABLE_CUSTOM_VOCABULARY=true
CUSTOM_VOCABULARY_PATH="config/custom_vocabulary.json"
ENABLE_TEXT_NORMALIZATION=true

# ===== ADVANCED FEATURES =====
ENABLE_NOISE_SUPPRESSION=true
NOISE_SUPPRESSION_LEVEL=0.3
ENABLE_ECHO_CANCELLATION=true
ENABLE_CONFIDENCE_FILTERING=true
MIN_CONFIDENCE_THRESHOLD=0.3

# ===== LOGGING =====
LOG_LEVEL=INFO
ENABLE_DETAILED_LOGGING=true
LOG_AUDIO_STATS=true
ENABLE_TIMESTAMPS=true

# ===== PERFORMANCE =====
NUM_WORKER_THREADS=2
AUDIO_BUFFER_SIZE=50
ENABLE_RECOVERY_MODE=true
MAX_RETRIES=3
RETRY_DELAY=1.0

# ===== CUSTOM VOCABULARY =====
PRIORITY_NAMES=Quip,Oracle,Byte,Mika,Kira
TECHNICAL_TERMS=API,database,server,client,frontend,backend
ABBREVIATIONS=AI,ML,NLP,UI,UX,API,HTTP,JSON,XML,SQL
EOF
        
        echo_success "Created default .env file"
        echo_info "You can customize the settings in .env file as needed"
    fi
    
    # Load environment variables safely
    while IFS='=' read -r key value || [[ -n "$key" ]]; do
        # Skip empty lines and comments
        [[ -z "$key" ]] || [[ "$key" =~ ^[[:space:]]*# ]] && continue
        
        # Remove leading/trailing whitespace
        key=$(echo "$key" | xargs)
        value=$(echo "$value" | xargs)
        
        # Remove quotes if present
        value="${value%\"}"
        value="${value#\"}"
        value="${value%\'}"
        value="${value#\'}"
        
        # Export the variable
        export "$key=$value"
    done < .env
    
    # Validate required variables
    if [[ -z "${VOSK_MODEL_PATH:-}" ]] || [[ -z "${VOSK_MODEL_URL:-}" ]]; then
        echo_error "VOSK_MODEL_PATH and VOSK_MODEL_URL must be set in .env"
        return 1
    fi
    
    echo_success "Environment configuration loaded"
    return 0
}

# --- Virtual Environment Management ---
setup_virtual_environment() {
    echo_step "Setting up Python virtual environment..."
    
    local venv_dir="venv"
    
    if [[ ! -d "$venv_dir" ]]; then
        echo_info "Creating virtual environment in '$venv_dir'..."
        python3 -m venv "$venv_dir"
        
        if [[ $? -ne 0 ]]; then
            echo_error "Failed to create virtual environment"
            echo_info "Make sure python3-venv is installed:"
            echo_info "  Ubuntu/Debian: sudo apt-get install python3-venv"
            echo_info "  CentOS/RHEL: sudo yum install python3-venv"
            return 1
        fi
        echo_success "Virtual environment created"
    else
        echo_info "Virtual environment already exists"
    fi
    
    # Activate virtual environment
    source "$venv_dir/bin/activate"
    echo_success "Virtual environment activated"
    
    # Upgrade pip and essential tools
    echo_info "Upgrading pip and essential tools..."
    python -m pip install --upgrade pip setuptools wheel --quiet
    
    if [[ $? -ne 0 ]]; then
        echo_warning "Failed to upgrade pip, continuing anyway..."
    else
        echo_success "Pip and tools upgraded"
    fi
    
    return 0
}

install_dependencies() {
    echo_step "Installing Python dependencies..."
    
    if [[ ! -f requirements.txt ]]; then
        echo_info "requirements.txt not found, creating default requirements..."
        cat > requirements.txt << 'EOF'
vosk>=0.3.45
sounddevice>=0.4.6
webrtcvad-wheels>=2.0.10
numpy>=1.21.0
python-dotenv>=0.19.0
nltk>=3.7
spellchecker>=0.4
textdistance>=4.2.1
psutil>=5.8.0
colorama>=0.4.4
rich>=12.0.0
tqdm>=4.64.0
EOF
        echo_success "Created default requirements.txt"
    fi
    
    # Install with progress indicator
    echo_info "Installing packages from requirements.txt..."
    
    # Install in chunks to provide better feedback
    local critical_packages="vosk sounddevice numpy webrtcvad-wheels python-dotenv"
    local optional_packages="nltk spellchecker textdistance psutil colorama rich tqdm"
    
    echo_info "Installing critical packages..."
    for package in $critical_packages; do
        echo_debug "Installing $package..."
        pip install "$package" --quiet
        
        if [[ $? -ne 0 ]]; then
            echo_error "Failed to install critical package: $package"
            return 1
        fi
    done
    echo_success "Critical packages installed"
    
    echo_info "Installing optional packages..."
    for package in $optional_packages; do
        echo_debug "Installing $package..."
        pip install "$package" --quiet
        
        if [[ $? -ne 0 ]]; then
            echo_warning "Failed to install optional package: $package (continuing anyway)"
        fi
    done
    echo_success "Package installation completed"
    
    # Verify critical imports
    echo_info "Verifying package installations..."
    python3 -c "
import vosk
import sounddevice
import webrtcvad
import numpy
print('✅ Critical packages verified')
" 2>/dev/null
    
    if [[ $? -ne 0 ]]; then
        echo_error "Package verification failed"
        return 1
    fi
    
    echo_success "All dependencies installed and verified"
    return 0
}

# --- Model Management ---
download_model() {
    echo_step "Checking Vosk model availability..."
    
    local model_dir="$VOSK_MODEL_PATH"
    local model_url="$VOSK_MODEL_URL"
    local model_zip_file=$(basename "$model_url")
    local model_unzipped_name="${model_zip_file%.zip}"
    
    if [[ -d "$model_dir" ]] && [[ -f "$model_dir/am/final.mdl" ]]; then
        echo_success "Vosk model already exists at '$model_dir'"
        return 0
    fi
    
    echo_info "Downloading Vosk model from $model_url..."
    echo_warning "This may take several minutes depending on your internet speed"
    
    # Create models directory
    mkdir -p "$(dirname "$model_dir")"
    
    # Download with progress
    local download_path="models/$model_zip_file"
    
    if check_command "wget"; then
        wget --progress=bar:force:noscroll -O "$download_path" "$model_url"
    elif check_command "curl"; then
        curl -# -L -o "$download_path" "$model_url"
    else
        echo_error "Neither wget nor curl available for downloading"
        return 1
    fi
    
    if [[ $? -ne 0 ]]; then
        echo_error "Failed to download model from $model_url"
        rm -f "$download_path"  # Clean up partial download
        return 1
    fi
    
    echo_success "Model downloaded successfully"
    
    # Extract the model
    echo_info "Extracting model archive..."
    unzip -q "$download_path" -d "models/"
    
    if [[ $? -ne 0 ]]; then
        echo_error "Failed to extract model archive"
        return 1
    fi
    
    # Move to correct location if needed
    if [[ "$model_unzipped_name" != "$(basename "$model_dir")" ]]; then
        mv "models/$model_unzipped_name" "$model_dir"
    fi
    
    # Clean up zip file
    rm -f "$download_path"
    
    # Verify model files
    local required_files=("am/final.mdl" "graph/HCLG.fst" "words.txt")
    for file in "${required_files[@]}"; do
        if [[ ! -f "$model_dir/$file" ]]; then
            echo_warning "Model file $file not found, model might be incomplete"
        fi
    done
    
    echo_success "Model extracted and verified at '$model_dir'"
    return 0
}

# --- Directory Structure Setup ---
setup_directory_structure() {
    echo_step "Setting up directory structure..."
    
    local directories=(
        "logs"
        "config" 
        "models"
        "processor"
        "controller"
        "data/audio_samples"
        "data/vocabulary"
        "tests"
    )
    
    for dir in "${directories[@]}"; do
        if [[ ! -d "$dir" ]]; then
            mkdir -p "$dir"
            echo_debug "Created directory: $dir"
        fi
    done
    
    # Create __init__.py files for Python modules
    local python_modules=("processor" "controller")
    for module in "${python_modules[@]}"; do
        if [[ ! -f "$module/__init__.py" ]]; then
            touch "$module/__init__.py"
            echo_debug "Created __init__.py in $module"
        fi
    done
    
    echo_success "Directory structure set up"
    return 0
}

# --- Configuration Validation ---
validate_configuration() {
    echo_step "Validating system configuration..."
    
    # Test audio system
    echo_info "Testing audio system..."
    python3 -c "
import sounddevice as sd
devices = sd.query_devices()
input_devices = [d for d in devices if d['max_input_channels'] > 0]
if not input_devices:
    raise Exception('No input audio devices found')
print(f'Found {len(input_devices)} input device(s)')
for i, device in enumerate(input_devices[:3]):  # Show first 3
    print(f'  {i}: {device[\"name\"]}')
" 2>/dev/null
    
    if [[ $? -ne 0 ]]; then
        echo_error "Audio system test failed"
        echo_info "Please ensure a microphone is connected and working"
        return 1
    fi
    
    # Test Vosk model loading
    echo_info "Testing Vosk model loading..."
    python3 -c "
import vosk
import os
model_path = os.getenv('VOSK_MODEL_PATH', 'models/vosk-model-en-in-0.5')
if not os.path.exists(model_path):
    raise Exception(f'Model path does not exist: {model_path}')
model = vosk.Model(model_path)
print('✅ Model loaded successfully')
" 2>/dev/null
    
    if [[ $? -ne 0 ]]; then
        echo_error "Vosk model test failed"
        echo_info "Please check your model path and files"
        return 1
    fi
    
    # Test WebRTC VAD
    echo_info "Testing Voice Activity Detection..."
    python3 -c "
import webrtcvad
vad = webrtcvad.Vad()
vad.set_mode(1)
print('✅ VAD initialized successfully')
" 2>/dev/null
    
    if [[ $? -ne 0 ]]; then
        echo_error "VAD test failed"
        return 1
    fi
    
    echo_success "Configuration validation passed"
    return 0
}

# --- Performance Optimization ---
optimize_system() {
    echo_step "Applying system optimizations..."
    
    # Set Python optimizations
    export PYTHONUNBUFFERED=1
    export PYTHONDONTWRITEBYTECODE=1
    
    # Audio system optimizations (Linux specific)
    if [[ "$(get_os_info)" == "linux" ]]; then
        # Check if we can optimize audio settings
        if [[ -w /proc/sys/kernel/sched_rt_runtime_us ]] 2>/dev/null; then
            echo_debug "Applying audio optimizations..."
            # These would require sudo, so we skip them in user mode
        fi
    fi
    
    echo_success "System optimizations applied"
    return 0
}

# --- Main Functions ---
show_banner() {
    echo -e "${WHITE}"
    echo "=================================================================="
    echo "🎤 Enhanced Speech Recognition System v2.0"
    echo "=================================================================="
    echo -e "${NC}"
    echo "🚀 Comprehensive voice-to-text solution with:"
    echo "   • Advanced noise suppression and VAD"
    echo "   • Custom vocabulary and grammar correction" 
    echo "   • Real-time processing with rich feedback"
    echo "   • Comprehensive error handling and recovery"
    echo "   • Detailed logging and analytics"
    echo ""
}

show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --help, -h          Show this help message"
    echo "  --setup-only        Only setup environment, don't start recognition"
    echo "  --skip-model        Skip model download (use existing model)"
    echo "  --debug             Enable debug output"
    echo "  --force-reinstall   Force reinstallation of dependencies"
    echo "  --test-only         Run system tests only"
    echo ""
    echo "Environment Variables:"
    echo "  DEBUG=true          Enable debug mode"
    echo "  FORCE_SETUP=true    Force complete setup"
    echo ""
}

run_system_tests() {
    echo_step "Running comprehensive system tests..."
    
    local test_script="tests/system_test.py"
    
    # Create a basic system test if it doesn't exist
    if [[ ! -f "$test_script" ]]; then
        mkdir -p tests
        cat > "$test_script" << 'EOF'
#!/usr/bin/env python3
"""System tests for Enhanced Speech Recognition System"""

import os
import sys
import unittest
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

class SystemTest(unittest.TestCase):
    def test_imports(self):
        """Test that all required modules can be imported"""
        try:
            import vosk
            import sounddevice as sd
            import webrtcvad
            import numpy as np
            from dotenv import load_dotenv
        except ImportError as e:
            self.fail(f"Failed to import required module: {e}")
    
    def test_model_exists(self):
        """Test that the Vosk model exists and is valid"""
        from dotenv import load_dotenv
        load_dotenv()
        
        model_path = os.getenv("VOSK_MODEL_PATH")
        self.assertIsNotNone(model_path, "VOSK_MODEL_PATH not set")
        self.assertTrue(os.path.exists(model_path), f"Model path does not exist: {model_path}")
        
        # Check for essential model files
        essential_files = ["am/final.mdl", "graph/HCLG.fst", "words.txt"]
        for file in essential_files:
            file_path = os.path.join(model_path, file)
            self.assertTrue(os.path.exists(file_path), f"Missing model file: {file}")
    
    def test_audio_devices(self):
        """Test that audio input devices are available"""
        import sounddevice as sd
        
        devices = sd.query_devices()
        input_devices = [d for d in devices if d['max_input_channels'] > 0]
        self.assertTrue(len(input_devices) > 0, "No input audio devices found")
    
    def test_vad_initialization(self):
        """Test Voice Activity Detection initialization"""
        import webrtcvad
        
        vad = webrtcvad.Vad()
        for mode in range(4):
            vad.set_mode(mode)  # Should not raise exception

if __name__ == '__main__':
    unittest.main()
EOF
    fi
    
    # Run the tests
    python3 "$test_script"
    local test_result=$?
    
    if [[ $test_result -eq 0 ]]; then
        echo_success "All system tests passed"
        return 0
    else
        echo_error "Some system tests failed"
        return 1
    fi
}

# --- Signal Handling ---
cleanup() {
    echo_info "Cleaning up..."
    
    # Kill any background processes
    local background_jobs=$(jobs -p 2>/dev/null || true)
    if [[ -n "$background_jobs" ]]; then
        echo "$background_jobs" | xargs -r kill 2>/dev/null || true
    fi
    
    # Deactivate virtual environment if active
    if [[ -n "${VIRTUAL_ENV:-}" ]]; then
        deactivate 2>/dev/null || true
    fi
    
    echo_success "Cleanup completed"
}

trap cleanup EXIT
trap 'echo_error "Script interrupted"; exit 130' INT TERM

# --- Main Script Logic ---
main() {
    local setup_only=false
    local skip_model=false  
    local force_reinstall=false
    local test_only=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            --help|-h)
                show_usage
                exit 0
                ;;
            --setup-only)
                setup_only=true
                shift
                ;;
            --skip-model)
                skip_model=true
                shift
                ;;
            --debug)
                export DEBUG=true
                shift
                ;;
            --force-reinstall)
                force_reinstall=true
                shift
                ;;
            --test-only)
                test_only=true
                shift
                ;;
            *)
                echo_error "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Show banner
    show_banner
    
    # System requirements check
    if ! check_system_requirements; then
        exit 1
    fi
    
    # Load environment
    if ! load_environment; then
        exit 1
    fi
    
    # Setup directory structure
    if ! setup_directory_structure; then
        exit 1
    fi
    
    # Setup virtual environment
    if ! setup_virtual_environment; then
        exit 1
    fi
    
    # Install dependencies
    if [[ "$force_reinstall" == "true" ]] || ! python3 -c "import vosk" 2>/dev/null; then
        if ! install_dependencies; then
            exit 1
        fi
    else
        echo_info "Dependencies already installed (use --force-reinstall to reinstall)"
    fi
    
    # Download model
    if [[ "$skip_model" != "true" ]]; then
        if ! download_model; then
            exit 1
        fi
    fi
    
    # Apply optimizations
    if ! optimize_system; then
        echo_warning "Some optimizations failed, continuing anyway"
    fi
    
    # Validate configuration
    if ! validate_configuration; then
        exit 1
    fi
    
    # Run tests if requested
    if [[ "$test_only" == "true" ]]; then
        if ! run_system_tests; then
            exit 1
        fi
        echo_success "System tests completed successfully"
        exit 0
    fi
    
    # Stop here if setup only
    if [[ "$setup_only" == "true" ]]; then
        echo_success "Setup completed successfully"
        echo_info "Run '$0' without --setup-only to start speech recognition"
        exit 0
    fi
    
    # Final system check
    echo_step "Performing final system check..."
    if ! run_system_tests; then
        echo_warning "Some tests failed, but continuing anyway"
    fi
    
    echo_success "🎉 Setup completed successfully!"
    echo ""
    echo_step "Starting Enhanced Speech Recognition System..."
    echo_info "Press Ctrl+C to stop the system at any time"
    echo ""
    
    # Start the main application
    if [[ -f "main.py" ]]; then
        python3 -u main.py
    else
        echo_error "main.py not found in current directory"
        echo_info "Please ensure the main application file exists"
        exit 1
    fi
}

# Execute main function with all arguments
main "$@"