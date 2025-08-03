#!/bin/bash

# --- Configuration ---
PYTHON_CMD="python3"
VENV_DIR="venv"
PYTHON_SCRIPT="main.py" # Change this to the name of your python script
MODEL_DIR="models/vosk-model-small-en-us-0.15"
MODEL_URL="https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
MODEL_ZIP_FILE="vosk-model-small-en-us-0.15.zip"

# --- Helper Functions ---
echo_info() {
    echo "[INFO] $1"
}

echo_error() {
    echo "[ERROR] $1" >&2
}

# 1. Check if Python 3 is installed
if ! command -v $PYTHON_CMD &> /dev/null; then
    echo_error "Python 3 is not installed. Please install it to continue."
    echo_info "On Debian/Ubuntu: sudo apt-get install python3 python3-pip python3-venv"
    echo_info "On macOS (using Homebrew): brew install python"
    exit 1
fi
echo_info "Python 3 is installed."

# 2. Check for and create the virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo_info "Creating Python virtual environment in '$VENV_DIR'..."
    $PYTHON_CMD -m venv $VENV_DIR
    if [ $? -ne 0 ]; then
        echo_error "Failed to create virtual environment."
        exit 1
    fi
else
    echo_info "Virtual environment already exists."
fi

# 3. Activate the virtual environment and install dependencies
# Activating the venv
source "$VENV_DIR/bin/activate"
echo_info "Virtual environment activated."

echo_info "Upgrading pip to the latest version..."
$PYTHON_CMD -m pip install --upgrade pip

echo_info "Installing required packages: vosk, sounddevice..."
pip install vosk sounddevice
if [ $? -ne 0 ]; then
    echo_error "Failed to install dependencies. Please check your internet connection and package names."
    # Deactivate venv on failure
    deactivate
    exit 1
fi
echo_info "Dependencies installed successfully."

# 4. Check for and download the Vosk model if it doesn't exist
if [ ! -d "$MODEL_DIR" ]; then
    echo_info "Vosk model not found. Attempting to download..."

    # Check for wget and unzip, and install them if they are missing
    if ! command -v wget &> /dev/null || ! command -v unzip &> /dev/null; then
        echo_info "'wget' or 'unzip' not found. Attempting to install them..."
        # OS-specific installation
        if [[ "$(uname)" == "Darwin" ]]; then # macOS
            if command -v brew &> /dev/null; then
                echo_info "Using Homebrew to install wget..."
                brew install wget
            else
                echo_error "Homebrew not found. Please install Homebrew to automatically install wget, or install wget manually."
                deactivate
                exit 1
            fi
        elif [[ "$(uname)" == "Linux" ]]; then # Linux
            if command -v apt-get &> /dev/null; then
                echo_info "Using apt-get to install wget and unzip. You may be prompted for your password."
                sudo apt-get update
                sudo apt-get install -y wget unzip
            elif command -v yum &> /dev/null; then
                echo_info "Using yum to install wget and unzip. You may be prompted for your password."
                sudo yum install -y wget unzip
            else
                echo_error "Could not find apt-get or yum. Please install 'wget' and 'unzip' manually."
                deactivate
                exit 1
            fi
        else
            echo_error "Unsupported OS. Please install 'wget' and 'unzip' manually."
            deactivate
            exit 1
        fi

        # Verify installation
        if ! command -v wget &> /dev/null || ! command -v unzip &> /dev/null; then
            echo_error "Failed to install 'wget' or 'unzip'. Please install them manually."
            deactivate
            exit 1
        fi
    fi
    
    # Download the model
    echo_info "Downloading model from $MODEL_URL..."
    wget $MODEL_URL
    if [ $? -ne 0 ]; then
        echo_error "Failed to download the model."
        deactivate
        exit 1
    fi

    # Unzip the model
    echo_info "Unzipping model..."
    unzip $MODEL_ZIP_FILE
    if [ $? -ne 0 ]; then
        echo_error "Failed to unzip the model."
        deactivate
        exit 1
    fi

    # Clean up the zip file
    rm $MODEL_ZIP_FILE
    echo_info "Model downloaded and unpacked successfully."
fi

# Final check for the model directory
if [ ! -d "$MODEL_DIR" ]; then
    echo_error "Vosk model directory '$MODEL_DIR' still not found after download attempt."
    deactivate
    exit 1
fi
echo_info "Vosk model found."

# 5. Run the main Python script
echo_info "Starting the speech recognition script..."
echo_info "Press Ctrl+C to stop the application."
$PYTHON_CMD $PYTHON_SCRIPT

# Deactivate the virtual environment upon exiting the script
deactivate
echo_info "Virtual environment deactivated. Script finished."
