#!/bin/bash

# Simple setup script for BackItUp application

PYTHON_CMD="python3"
VENV_DIR="BackItUp/.venv"
REQUIREMENTS_FILE="BackItUp/requirements.txt" # Use requirements file

echo "--- BackItUp Setup ---"

# Check for Python 3
if ! command -v $PYTHON_CMD &> /dev/null
then
    echo "Error: $PYTHON_CMD command not found. Please install Python 3."
    exit 1
fi
echo "Found $PYTHON_CMD: $($PYTHON_CMD --version)"

# Check if venv module is available
if ! $PYTHON_CMD -m venv --help &> /dev/null
then
    echo "Error: Python 3 'venv' module not found. It might need to be installed (e.g., sudo apt install python3-venv)."
    exit 1
fi
echo "Python 'venv' module found."

# Create virtual environment if it doesn't exist
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating virtual environment in $VENV_DIR..."
    $PYTHON_CMD -m venv "$VENV_DIR"
    if [ $? -ne 0 ]; then
        echo "Error: Failed to create virtual environment."
        exit 1
    fi
    echo "Virtual environment created."
else
    echo "Virtual environment already exists in $VENV_DIR."
fi

# Check if requirements file exists
if [ ! -f "$REQUIREMENTS_FILE" ]; then
    echo "Error: Requirements file not found at $REQUIREMENTS_FILE"
    exit 1
fi

# Activate virtual environment (for installing packages) and install requirements
echo "Installing required packages from $REQUIREMENTS_FILE..."
source "$VENV_DIR/bin/activate" && pip install -r "$REQUIREMENTS_FILE"

if [ $? -ne 0 ]; then
    echo "Error: Failed to install required packages."
    # Deactivate manually if activation succeeded but pip failed
    deactivate &> /dev/null
    exit 1
fi

# Deactivate after installation (user needs to activate manually to run)
deactivate &> /dev/null

echo ""
echo "--- Setup Complete ---"
echo ""
echo "To run the application:"
echo "1. Activate the virtual environment: source $VENV_DIR/bin/activate"
echo "2. Run the main script: python -m BackItUp.main"
echo "3. When finished, deactivate: deactivate"
echo ""

exit 0
