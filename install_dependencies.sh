#!/bin/bash
echo "Installing dependencies for Spring Force Test File Converter..."

# Check if Python is installed
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed or not in the PATH."
    echo "Please install Python 3 using your package manager."
    exit 1
fi

# Upgrade pip and install dependencies
python3 -m pip install --upgrade pip
python3 -m pip install tk

echo ""
echo "Dependencies installed successfully."
echo ""
echo "You can now run the application using ./run_converter.sh" 