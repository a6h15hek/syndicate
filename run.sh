#!/bin/bash

# --- Configuration ---
PYTHON_CMD="python3"
VENV_DIR="venv"
PYTHON_SCRIPT="main.py"
# Updated to use the medium Indian-English model
MODEL_DIR="models/vosk-model-en-in-0.5"
MODEL_URL="https://alphacephei.com/vosk/models/vosk-model-en-in-0.5.zip"
MODEL_ZIP_FILE="vosk-model-en-in-0.5.zip"
MODEL_UNZIPPED_NAME="vosk-model-en-in-0.5" # The name of the folder inside the zip

# --- Helper Functions ---
echo_info() {
    echo -e "\e[34m[INFO]\e[0m $1"
}

echo_error() {
    echo -e "\e[31m[ERROR]\e[0m $1" >&2
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
source "$VENV_DIR/bin/activate"
echo_info "Virtual environment activated."

echo_info "Upgrading pip to the latest version..."
pip install --upgrade pip > /dev/null

echo_info "Installing required packages from requirements.txt..."
pip install -r requirements.txt
if [ $? -ne 0 ]; then
    echo_error "Failed to install dependencies from requirements.txt."
    deactivate
    exit 1
fi
echo_info "Dependencies installed successfully."

# 4. Check for and download the Vosk model if it doesn't exist
if [ ! -d "$MODEL_DIR" ]; then
    echo_info "Vosk model not found. Attempting to download..."
    
    # Create parent directory for models
    mkdir -p models

    # Check for wget and unzip
    if ! command -v wget &> /dev/null || ! command -v unzip &> /dev/null; then
        echo_error "'wget' and 'unzip' are required. Please install them."
        echo_info "On Debian/Ubuntu: sudo apt-get install wget unzip"
        echo_info "On macOS (using Homebrew): brew install wget"
        deactivate
        exit 1
    fi
    
    # Download the model
    echo_info "Downloading model from $MODEL_URL..."
    wget -q --show-progress -O "$MODEL_ZIP_FILE" "$MODEL_URL"
    if [ $? -ne 0 ]; then
        echo_error "Failed to download the model."
        deactivate
        exit 1
    fi

    # Unzip the model
    echo_info "Unzipping model..."
    unzip -q "$MODEL_ZIP_FILE" -d "models/"
    if [ $? -ne 0 ]; then
        echo_error "Failed to unzip the model."
        rm "$MODEL_ZIP_FILE" # Clean up failed download
        deactivate
        exit 1
    fi
    
    # Rename the unzipped folder if necessary
    if [ -d "models/$MODEL_UNZIPPED_NAME" ] && [ "$MODEL_DIR" != "models/$MODEL_UNZIPPED_NAME" ]; then
        echo_info "Renaming model directory to '$MODEL_DIR'..."
        mv "models/$MODEL_UNZIPPED_NAME" "$MODEL_DIR"
    fi

    # Clean up the zip file
    rm "$MODEL_ZIP_FILE"
    echo_info "Model downloaded and unpacked successfully."
fi

# Final check for the model directory
if [ ! -d "$MODEL_DIR" ]; then
    echo_error "Vosk model directory '$MODEL_DIR' still not found after download attempt."
    deactivate
    exit 1
fi
echo_info "Vosk Indian English model found."

# 5. Run the main Python script
echo_info "Starting the speech recognition script..."
echo_info "Press Ctrl+C to stop the application."
$PYTHON_CMD -u $PYTHON_SCRIPT # -u for unbuffered output

# Deactivate the virtual environment upon exiting the script
deactivate
echo_info "Virtual environment deactivated. Script finished."
