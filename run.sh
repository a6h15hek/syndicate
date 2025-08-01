#!/bin/bash

# ---
# A script to set up and run the Python environment for the project.
#
# This script will:
# 1. Check for and install Homebrew if it's missing.
# 2. Check for and install python@3.11 using Homebrew.
# 3. Create a virtual environment named 'venv' if it doesn't exist.
# 4. Upgrade pip and install packages from requirements.txt.
# 5. Run the main.py script and ensure it can be stopped with Ctrl+C.
#
# The script is designed to be idempotent, meaning it can be run multiple
# times without causing issues. It checks for existing installations
# and environments to avoid re-running unnecessary commands.
# ---

# Initialize a variable to hold the Python process ID
PYTHON_PID=""

# Function to handle script interruption (Ctrl+C)
cleanup() {
    echo -e "\n\nScript interrupted. Exiting gracefully."

    # If the PYTHON_PID variable is set and the process exists, kill it.
    if [ -n "$PYTHON_PID" ] && ps -p $PYTHON_PID > /dev/null; then
        echo "Stopping Python application (PID: $PYTHON_PID)..."
        kill $PYTHON_PID
    fi

    # Deactivate virtual environment if it was activated by this script's context
    if type deactivate &>/dev/null; then
        deactivate
    fi
    exit 1
}

# Trap SIGINT (Ctrl+C) and call the cleanup function
trap cleanup SIGINT

# --- Step 1: Check for Homebrew ---
echo "--- Checking for Homebrew ---"
if ! command -v brew &> /dev/null; then
    echo "Homebrew not found. Please install it from https://brew.sh/"
    exit 1
fi
echo "Homebrew is installed."
echo ""

# --- Step 2: Check and Install Python 3.11 ---
echo "--- Checking for Python 3.11 ---"
# Check if python@3.11 is listed by brew. The command exits with 0 if found.
if brew list python@3.11 &>/dev/null; then
    echo "Python 3.11 is already installed via Homebrew."
else
    echo "Python 3.11 not found. Installing with Homebrew..."
    brew install python@3.11
    if [ $? -ne 0 ]; then
        echo "Failed to install Python 3.11. Please check your Homebrew setup."
        exit 1
    fi
    echo "Python 3.11 installed successfully."
fi
echo ""

# --- Step 3: Check and Create Virtual Environment ---
VENV_DIR="venv"
echo "--- Checking for virtual environment ('$VENV_DIR') ---"
if [ -d "$VENV_DIR" ]; then
    echo "Virtual environment '$VENV_DIR' already exists."
else
    echo "Creating virtual environment '$VENV_DIR' with python3.11..."
    python3.11 -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment."
        exit 1
    fi
    echo "Virtual environment created successfully."
fi
echo ""

# --- Step 4: Activate Environment and Install Dependencies ---
echo "--- Activating virtual environment and installing dependencies ---"

# Activate the virtual environment for the rest of the script
source "$VENV_DIR/bin/activate"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip
if [ $? -ne 0 ]; then
    echo "Failed to upgrade pip."
    cleanup
    exit 1
fi

# Install requirements
if [ -f "requirements.txt" ]; then
    echo "Installing dependencies from requirements.txt..."
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Failed to install dependencies from requirements.txt."
        cleanup
        exit 1
    fi
    echo "Dependencies installed."
else
    echo "Warning: requirements.txt not found. Skipping dependency installation."
fi
echo ""

# --- Step 5: Run the Python Application ---
echo "--- Starting the application (main.py) ---"
if [ -f "main.py" ]; then
    # Run the python script in the background and store its PID
    python3.11 main.py &
    PYTHON_PID=$!
    
    # Wait for the python script to finish. 
    # The 'trap' will interrupt this 'wait' command, allowing cleanup to run.
    wait $PYTHON_PID
else
    echo "Error: main.py not found. Cannot start the application."
    cleanup
    exit 1
fi

# Deactivate on normal exit
deactivate
echo -e "\n--- Script finished ---"
