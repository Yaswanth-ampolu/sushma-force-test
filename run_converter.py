import struct
import re
import os
import sys
from pathlib import Path

def parse_text_file(input_file):
    """Parse the text file and extract key-value pairs and test sequence data."""
    with open(input_file, 'r') as f:
        content = f.read()
    
    # Extract header information and test sequence
    header_match = re.search(r'(.*?)<Test Sequence>(.*)', content, re.DOTALL)
    if not header_match:
        print("Error: Could not find test sequence section")
        return None
    
    header_section = header_match.group(1)
    test_sequence = header_match.group(2)
    
    # Parse header key-value pairs
    header_data = {}
    for line in header_section.split('\n'):
        if line.strip():
            # Detect if the line has a column structure (number-key-value)
            parts = re.split(r'(\d+)', line.strip(), 1)
            if len(parts) >= 3:
                column_number = parts[1]
                rest = parts[2]
                key_value = rest.split('--', 1) if '--' in rest else rest.split('mm', 1)
                if len(key_value) == 2:
                    key, value = key_value
                    header_data[key.strip()] = value.strip()
                elif len(key_value) == 1 and 'mm' in rest:
                    key = parts[1]  # Use the column number as key
                    value = rest.strip()
                    header_data[key] = value
    
    # Parse test sequence
    test_steps = []
    for line in test_sequence.split('\n'):
        if line.strip():
            # Try to extract command and parameters
            command_match = re.match(r'([A-Za-z]+\(?\w*\)?)(.*)', line)
            if command_match:
                command = command_match.group(1)
                params = command_match.group(2).strip()
                test_steps.append((command, params))
    
    return {
        'header': header_data,
        'test_sequence': test_steps
    }

def convert_to_binary(parsed_data, input_file):
    """Convert the parsed data to binary format."""
    try:
        # Create output directory if it doesn't exist
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True)
        
        # Generate output filename based on input filename
        input_path = Path(input_file)
        output_file = output_dir / f"{input_path.stem}.bin"
        
        with open(output_file, 'wb') as f:
            # Write a simple header/identifier (4 bytes)
            f.write(b'TSTH')  # Test Sequence Test Header
            
            # Write the number of header items (4 bytes)
            header_count = len(parsed_data['header'])
            f.write(struct.pack('I', header_count))
            
            # Write each header item
            for key, value in parsed_data['header'].items():
                # Key length (1 byte), key (variable), value length (1 byte), value (variable)
                key_bytes = key.encode('utf-8')
                f.write(struct.pack('B', len(key_bytes)))
                f.write(key_bytes)
                
                value_bytes = value.encode('utf-8')
                f.write(struct.pack('B', len(value_bytes)))
                f.write(value_bytes)
            
            # Write the number of test steps (4 bytes)
            test_count = len(parsed_data['test_sequence'])
            f.write(struct.pack('I', test_count))
            
            # Write each test step
            for command, params in parsed_data['test_sequence']:
                # Command length (1 byte), command (variable), params length (1 byte), params (variable)
                cmd_bytes = command.encode('utf-8')
                f.write(struct.pack('B', len(cmd_bytes)))
                f.write(cmd_bytes)
                
                params_bytes = params.encode('utf-8')
                f.write(struct.pack('B', len(params_bytes)))
                f.write(params_bytes)
            
            # Write EOF marker
            f.write(b'EOTS')  # End Of Test Sequence
            
        return True, output_file

    except Exception as e:
        print(f"Error writing file: {e}")
        return False, None

def main():
    # Handle command line argument if provided
    if len(sys.argv) > 1:
        input_file = sys.argv[1]
    else:
        input_file = input("Enter the path to the text file: ").strip()

    if not input_file:
        print("Error: No input file specified")
        return

    # Convert relative path to absolute
    input_path = Path(input_file).resolve()
    if not input_path.exists():
        print(f"Error: Input file '{input_path}' does not exist")
        return

    try:
        parsed_data = parse_text_file(input_path)
        success, output_path = convert_to_binary(parsed_data, input_file)
        
        if success:
            print(f"Conversion completed. Binary file saved to: {output_path}")
        else:
            print("Failed to convert the file.")
    except Exception as e:
        print(f"Unexpected error: {e}")

if __name__ == "__main__":
    main()