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

# --- Load Environment Variables ---
# Check for the .env file and load its variables. This is crucial for configuration.
if [ -f .env ]; then
    echo_info "Loading environment variables from .env file..."
    # Export the variables from .env to be available to this script
    export $(cat .env | sed 's/#.*//g' | xargs)
else
    echo_error ".env file not found. Please create one with VOSK_MODEL_PATH and VOSK_MODEL_URL."
    exit 1
fi

# --- Configuration (from .env) ---
PYTHON_CMD="python3"
VENV_DIR="venv"
PYTHON_SCRIPT="main.py"

# Model configuration is now dynamically set from the loaded environment variables
MODEL_DIR=${VOSK_MODEL_PATH}
MODEL_URL=${VOSK_MODEL_URL}
MODEL_ZIP_FILE=$(basename "$MODEL_URL")
# The name of the folder inside the zip file (e.g., "vosk-model-en-in-0.5")
MODEL_UNZIPPED_NAME="${MODEL_ZIP_FILE%.zip}"

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
    echo_info "Downloading model from $MODEL_URL..."
    wget -q --show-progress -P models/ "$MODEL_URL"
    if [ $? -ne 0 ]; then
        echo_error "Failed to download the model."
        deactivate
        exit 1
    fi

    # Unzip in models directory
    echo_info "Unzipping model..."
    unzip -q "models/$MODEL_ZIP_FILE" -d "models/"
    if [ $? -ne 0 ]; then
        echo_error "Failed to unzip the model."
        rm "models/$MODEL_ZIP_FILE" # Clean up failed download
        deactivate
        exit 1
    fi
    
    # Clean up the zip file
    rm "models/$MODEL_ZIP_FILE"
    echo_info "Model downloaded and unpacked successfully in 'models/'."
fi

# Final check for the model directory
if [ ! -d "$MODEL_DIR" ]; then
    echo_error "Vosk model directory '$MODEL_DIR' still not found after download attempt."
    deactivate
    exit 1
fi
echo_info "Vosk model found at '$MODEL_DIR'."

# 5. Run the main Python script
echo_info "Starting the speech recognition script..."
echo_info "Press Ctrl+C to stop the application."
$PYTHON_CMD -u $PYTHON_SCRIPT # -u for unbuffered output

# Deactivate the virtual environment upon exiting the script
deactivate
echo_info "Virtual environment deactivated. Script finished."
