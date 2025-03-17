#!/bin/bash
echo "Starting Spring Force Test File Converter..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in the PATH."
    echo "Please install Python 3 or run ./install_dependencies.sh first."
    exit 1
fi

# Run the application
python3 gui.py
if [ $? -ne 0 ]; then
    echo "Error starting application. Please check if all dependencies are installed."
    echo "Run ./install_dependencies.sh to install required packages."
    exit 1
fi 