# Spring Force Test File Converter

This project provides tools to convert binary spring force test files to human-readable text format and back again.

## Quick Start

### Windows
1. Run `install_dependencies.bat` to install required dependencies
2. Run `run_converter.bat` to start the application

### Linux/Mac
1. Run `chmod +x *.sh` to make the shell scripts executable
2. Run `./install_dependencies.sh` to install required dependencies
3. Run `./run_converter.sh` to start the application

## Tools

### 1. GUI Application (gui.py)

The easiest way to use the converter is through the graphical user interface.

#### Usage

```bash
python gui.py  # Windows
python3 gui.py # Linux/Mac
```

#### Features

- Convert binary files to text/JSON format
- Convert text files back to binary format
- View and edit converted files
- Save and open files with default applications
- Track recently used files

### 2. Encoder (encoder.py)

The encoder tool converts binary spring force test files to human-readable text format.

#### Usage

```bash
python encoder.py [input_files_or_directories] [options]
```

#### Options

- `-o, --output`: Specify output directory for converted files
- `-f, --format`: Output format (txt, json, or all)
- `-r, --recursive`: Process directories recursively
- `-v, --verbose`: Enable verbose output

#### Example

```bash
# Convert a single file
python encoder.py "DATA/AS 01~Comp-Deflection"

# Convert all files in a directory
python encoder.py DATA -r

# Convert and save as both text and JSON
python encoder.py "DATA/AS 01~Comp-Deflection" -f all
```

### 3. Decoder (reverser.py)

The decoder tool converts text files back to binary format.

#### Usage

```bash
python reverser.py [input_text_files_or_directories] [options]
```

#### Options

- `-o, --output`: Specify output directory for converted binary files
- `-r, --recursive`: Process directories recursively
- `-v, --verbose`: Enable verbose output

#### Example

```bash
# Convert a single text file back to binary
python reverser.py "DATA/output/AS_01_Comp-Deflection.txt"

# Convert all text files in a directory
python reverser.py DATA/output -r
```

## File Format

### Binary Format

The binary files use a length-prefixed string format:
- 4-byte length prefix (big endian)
- String data (UTF-8 encoded)

### Text Format

The text files have a simple structure:
```
Part Number: [part number]
Model Number: [model number]
Free Length: [length] mm

--- Test Sequence ---
[command] - [description]: [parameters]
...
```

## Common Commands

- `ZF`: Zero Force - Reset the force sensor to zero
- `ZD`: Zero Displacement - Reset position measurement
- `TH`: Threshold (Search Contact) - Find contact with the spring
- `FL(P)`: Measure Free Length - Measure uncompressed spring length
- `Mv(P)`: Move to Position - Move to specific displacement
- `Scrag`: Scragging - Pre-load spring before testing
- `Fr(P)`: Force at Position - Measure force at specific position
- `TD`: Time Delay - Add waiting period
- `PMsg`: User Message - Display operator messages
- `LP`: Loop - Create repetitive sequences

## Troubleshooting

If you encounter issues with the conversion:

1. Check the hex dump files to understand the binary structure
2. Ensure the text files follow the expected format
3. For complex files, try using the `-v` verbose flag for more detailed output

## Requirements

- Python 3.6+
- Tkinter (for GUI application)
- No external dependencies required

## Sample Files

The `DATA/samples` directory contains sample files for testing:
- `AS 01~Comp-Deflection`: Binary file example
- `AS_01_Comp-Deflection.txt`: Text file example 