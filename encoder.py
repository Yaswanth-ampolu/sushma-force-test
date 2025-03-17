#!/usr/bin/env python3

import sys
import os
import struct
import argparse
import json
from pathlib import Path

def create_hex_dump(data, bytes_per_line=16):
    """
    Create a hex dump of binary data.
    
    Args:
        data: Binary data as bytes or bytearray
        bytes_per_line: Number of bytes to display per line
        
    Returns:
        String containing the hex dump
    """
    result = []
    for i in range(0, len(data), bytes_per_line):
        chunk = data[i:i+bytes_per_line]
        hex_values = ' '.join(f'{b:02X}' for b in chunk)
        ascii_values = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
        result.append(f'{i:08X}  {hex_values:<{bytes_per_line*3}}  |{ascii_values}|')
    return '\n'.join(result)

def extract_string(data, offset):
    """
    Extract a length-prefixed string from binary data.
    
    Args:
        data: Binary data as bytes or bytearray
        offset: Offset to start reading from
        
    Returns:
        Tuple of (string, new_offset)
    """
    # Check if we have enough data
    if offset + 4 > len(data):
        return "", offset
    
    try:
        # Read the 4-byte length prefix (big endian)
        length = struct.unpack('>I', data[offset:offset+4])[0]
        offset += 4
        
        # Sanity check for length
        if length > 1000 or offset + length > len(data):
            # This might not be a valid string, return empty
            return "", offset - 4
        
        # Read the string data
        string_data = data[offset:offset+length]
        offset += length
        
        # Decode the string as UTF-8
        try:
            string = string_data.decode('utf-8', errors='replace')
        except:
            string = string_data.decode('latin-1', errors='replace')
        
        return string, offset
    except:
        # If any error occurs, return empty string and original offset
        return "", offset

def process_binary_file(binary_file_path, verbose=False):
    """
    Process a binary file and extract its contents.
    
    Args:
        binary_file_path: Path to the binary file
        verbose: Whether to print verbose output
        
    Returns:
        Dictionary containing the extracted data
    """
    with open(binary_file_path, 'rb') as f:
        data = f.read()
    
    if verbose:
        print(f"File size: {len(data)} bytes")
    
    # Initialize result structure
    result = {
        "metadata": {},
        "parameters": [],
        "test_sequence": []
    }
    
    # Try to determine file format based on header
    if len(data) < 13:
        if verbose:
            print("File too small to be a valid spring force test file")
        return result
    
    # Check for standard header pattern
    header_pattern = data[:13]
    standard_header = b'\x00\x00\x00\x12\x00\x00\x00\x06\x00\x00\x00\x01\x31'
    
    if header_pattern != standard_header:
        if verbose:
            print("Warning: Non-standard file header detected")
            print(f"Expected: {standard_header.hex()}")
            print(f"Found: {header_pattern.hex()}")
    
    # Start parsing after header
    offset = 13
    
    # Extract metadata
    metadata = {}
    test_sequence = []
    
    # First try to extract part number, model number, and free length
    try:
        # Part Number
        key, offset = extract_string(data, offset)
        if key == "Part Number":
            _, offset = extract_string(data, offset)  # Skip the "--" separator
            value, offset = extract_string(data, offset)
            metadata["Part Number"] = value
            
            # Model Number
            key, offset = extract_string(data, offset)
            if key == "Model Number":
                _, offset = extract_string(data, offset)  # Skip the "--" separator
                value, offset = extract_string(data, offset)
                metadata["Model Number"] = value
                
                # Free Length
                key, offset = extract_string(data, offset)
                if key == "Free Length":
                    unit, offset = extract_string(data, offset)
                    value, offset = extract_string(data, offset)
                    metadata["Free Length"] = f"{value} {unit}"
        
        # Look for test sequence marker
        test_seq_found = False
        search_offset = offset
        while search_offset < len(data) - 4 and not test_seq_found:
            try:
                key, new_offset = extract_string(data, search_offset)
                if key == "<Test Sequence>":
                    offset = new_offset
                    test_seq_found = True
                    break
                search_offset += 1
            except:
                search_offset += 1
            
        # If we found the test sequence marker, extract force unit
        if test_seq_found:
            force_unit, offset = extract_string(data, offset)
            metadata["Force Unit"] = force_unit
            
            # Skip some fixed values
            _, offset = extract_string(data, offset)  # Skip the "--" separator
            _, offset = extract_string(data, offset)  # Skip "Height"
            _, offset = extract_string(data, offset)  # Skip height value
            _, offset = extract_string(data, offset)  # Skip force range
            
            # Process commands until end of file
            row_index = 0
            while offset < len(data) - 4:
                try:
                    cmd, offset = extract_string(data, offset)
                    if not cmd:  # Skip empty commands
                        continue
                    
                    # Create a command entry
                    command_entry = {
                        "Row": f"R{row_index:02d}",
                        "Command": cmd,
                        "Description": "",
                        "Condition": "",
                        "Unit": "",
                        "Tolerance": "",
                        "Speed": ""
                    }
                    
                    # Process based on command type
                    if cmd == "ZF":
                        description, offset = extract_string(data, offset)
                        command_entry["Description"] = description
                        # Skip padding bytes if present
                        if offset + 16 <= len(data):
                            padding_check = data[offset:offset+4]
                            if all(b == 0 for b in padding_check):
                                offset += 16
                    
                    elif cmd == "ZD":
                        description, offset = extract_string(data, offset)
                        command_entry["Description"] = description
                        # Skip padding bytes if present
                        if offset + 16 <= len(data):
                            padding_check = data[offset:offset+4]
                            if all(b == 0 for b in padding_check):
                                offset += 16
                    
                    elif cmd == "TH":
                        description, offset = extract_string(data, offset)
                        force, offset = extract_string(data, offset)
                        unit, offset = extract_string(data, offset)
                        value, offset = extract_string(data, offset)
                        
                        command_entry["Description"] = description
                        command_entry["Condition"] = force
                        command_entry["Unit"] = unit
                        command_entry["Tolerance"] = value
                    
                    elif cmd == "FL(P)":
                        description, offset = extract_string(data, offset)
                        unit, offset = extract_string(data, offset)
                        value, offset = extract_string(data, offset)
                        
                        command_entry["Description"] = description
                        command_entry["Unit"] = unit
                        command_entry["Tolerance"] = value
                    
                    elif cmd == "Mv(P)":
                        description, offset = extract_string(data, offset)
                        position, offset = extract_string(data, offset)
                        unit, offset = extract_string(data, offset)
                        target, offset = extract_string(data, offset)
                        
                        command_entry["Description"] = description
                        command_entry["Condition"] = position
                        command_entry["Unit"] = unit
                        command_entry["Tolerance"] = target
                    
                    elif cmd == "Fr(P)":
                        description, offset = extract_string(data, offset)
                        unit, offset = extract_string(data, offset)
                        value, offset = extract_string(data, offset)
                        
                        command_entry["Description"] = description
                        command_entry["Unit"] = unit
                        command_entry["Tolerance"] = value
                    
                    elif cmd == "TD":
                        description, offset = extract_string(data, offset)
                        time, offset = extract_string(data, offset)
                        unit, offset = extract_string(data, offset)
                        
                        command_entry["Description"] = description
                        command_entry["Condition"] = time
                        command_entry["Unit"] = unit
                    
                    elif cmd == "Scrag":
                        description, offset = extract_string(data, offset)
                        value, offset = extract_string(data, offset)
                        
                        command_entry["Description"] = description
                        command_entry["Condition"] = value
                        
                        # Skip padding bytes if present
                        if offset + 16 <= len(data):
                            padding_check = data[offset:offset+4]
                            if all(b == 0 for b in padding_check):
                                offset += 16
                    
                    elif cmd == "PMsg":
                        description, offset = extract_string(data, offset)
                        message, offset = extract_string(data, offset)
                        
                        command_entry["Description"] = description
                        command_entry["Condition"] = message
                        
                        # Skip padding bytes if present
                        if offset + 16 <= len(data):
                            padding_check = data[offset:offset+4]
                            if all(b == 0 for b in padding_check):
                                offset += 16
                    
                    elif cmd == "LP":
                        description, offset = extract_string(data, offset)
                        loop_info, offset = extract_string(data, offset)
                        
                        command_entry["Description"] = description
                        command_entry["Condition"] = loop_info
                        
                        # Skip padding bytes if present
                        if offset + 16 <= len(data):
                            padding_check = data[offset:offset+4]
                            if all(b == 0 for b in padding_check):
                                offset += 16
                    
                    else:
                        # Unknown command, try to extract next strings
                        for _ in range(3):  # Try to extract up to 3 more strings
                            if offset < len(data) - 4:
                                value, offset = extract_string(data, offset)
                                if not value:
                                    break
                    
                    # Add command to test sequence if it has a valid command
                    if command_entry["Command"]:
                        test_sequence.append(command_entry)
                        row_index += 1
                
                except Exception as e:
                    if verbose:
                        print(f"Error processing command at offset {offset}: {str(e)}")
                    # Try to recover by moving to the next potential string
                    offset += 1
    
    except Exception as e:
        if verbose:
            print(f"Error processing file: {str(e)}")
    
    # Store results
    result["metadata"] = metadata
    result["test_sequence"] = test_sequence
    
    if verbose:
        print(f"Extracted metadata: {metadata}")
        print(f"Extracted {len(test_sequence)} test sequence commands")
    
    return result

def format_as_text(data):
    """
    Format the extracted data as a human-readable text file.
    
    Args:
        data: Dictionary containing the extracted data
        
    Returns:
        String containing the formatted text
    """
    lines = []
    
    # Add metadata
    for key, value in data["metadata"].items():
        if key != "Force Unit":  # Skip force unit as it's internal
            lines.append(f"{key}: {value}")
    
    # Add test sequence header
    lines.append("")
    lines.append("--- Test Sequence ---")
    
    # Add test sequence
    for cmd in data["test_sequence"]:
        command = cmd["Command"]
        description = cmd["Description"]
        condition = cmd["Condition"]
        unit = cmd["Unit"]
        tolerance = cmd["Tolerance"]
        
        # Format based on command type
        if command == "ZF":
            lines.append(f"{command} - {description}")
        
        elif command == "ZD":
            lines.append(f"{command} - {description}")
        
        elif command == "TH":
            lines.append(f"{command} - {description}: {condition} {unit}, Value: {tolerance}")
        
        elif command == "FL(P)":
            lines.append(f"{command} - {description}: {tolerance}")
        
        elif command == "Mv(P)":
            if unit:
                lines.append(f"{command} - {description}: {condition} {unit}, Target: {tolerance}")
            else:
                lines.append(f"{command} - {description}: {condition}, Target: {tolerance}")
        
        elif command == "Fr(P)":
            lines.append(f"{command} - {description}: {tolerance}")
        
        elif command == "TD":
            lines.append(f"{command} - {description}: {condition} {unit}")
        
        elif command == "Scrag":
            lines.append(f"{command} - {description}: {condition}")
        
        elif command == "PMsg":
            lines.append(f"{command} - {description}: {condition}")
        
        elif command == "LP":
            lines.append(f"{command} - {description}: {condition}")
        
        else:
            # Generic format for unknown commands
            parts = [command]
            if description:
                parts.append(description)
            if condition:
                parts.append(condition)
            if unit:
                parts.append(unit)
            if tolerance:
                parts.append(tolerance)
            
            lines.append(" - ".join(parts))
    
    return "\n".join(lines)

def process_file(input_file, output_dir, output_format="all", verbose=False):
    """
    Process a single binary file and convert it to text/JSON.
    
    Args:
        input_file: Path to the input binary file
        output_dir: Directory to save output files
        output_format: Output format (txt, json, or all)
        verbose: Whether to print verbose output
        
    Returns:
        Tuple of (success, error_message)
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "encoder"), exist_ok=True)
        
        # Process the binary file
        data = process_binary_file(input_file, verbose)
        
        # Generate base output filename
        base_name = Path(input_file).stem.replace('~', '_').replace(' ', '_')
        
        # Create hex dump
        with open(input_file, 'rb') as f:
            binary_data = f.read()
        
        hex_dump = create_hex_dump(binary_data)
        hex_output_path = os.path.join(output_dir, "encoder", f"{base_name}_hex_dump.txt")
        with open(hex_output_path, 'w', encoding='utf-8') as f:
            f.write(hex_dump)
        
        # Save as text if requested
        if output_format in ['txt', 'all']:
            text_output = format_as_text(data)
            txt_output_path = os.path.join(output_dir, f"{base_name}.txt")
            with open(txt_output_path, 'w', encoding='utf-8') as f:
                f.write(text_output)
        
        # Save as JSON if requested
        if output_format in ['json', 'all']:
            json_output_path = os.path.join(output_dir, f"{base_name}.json")
            with open(json_output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        
        return True, ""
    
    except Exception as e:
        error_message = f"Error processing file {input_file}: {str(e)}"
        if verbose:
            print(error_message)
        return False, error_message

def process_directory(input_dir, output_dir, output_format="all", recursive=False, verbose=False):
    """
    Process all binary files in a directory.
    
    Args:
        input_dir: Directory containing input binary files
        output_dir: Directory to save output files
        output_format: Output format (txt, json, or all)
        recursive: Whether to process subdirectories recursively
        verbose: Whether to print verbose output
        
    Returns:
        Tuple of (success_count, error_count)
    """
    success_count = 0
    error_count = 0
    
    # Get list of files to process
    if recursive:
        files = []
        for root, _, filenames in os.walk(input_dir):
            for filename in filenames:
                if not filename.endswith('.txt') and not filename.endswith('.json'):
                    files.append(os.path.join(root, filename))
    else:
        files = [os.path.join(input_dir, f) for f in os.listdir(input_dir) 
                if os.path.isfile(os.path.join(input_dir, f)) 
                and not f.endswith('.txt') and not f.endswith('.json')]
    
    # Process each file
    for file_path in files:
        if verbose:
            print(f"Processing {file_path}...")
        
        success, error = process_file(file_path, output_dir, output_format, verbose)
        
        if success:
            success_count += 1
        else:
            error_count += 1
            if verbose:
                print(error)
    
    return success_count, error_count

def main():
    parser = argparse.ArgumentParser(description='Convert binary spring force test files to text/JSON format.')
    parser.add_argument('input', nargs='+', help='Input binary files or directories')
    parser.add_argument('-o', '--output', default='output', help='Output directory')
    parser.add_argument('-f', '--format', choices=['txt', 'json', 'all'], default='all', help='Output format')
    parser.add_argument('-r', '--recursive', action='store_true', help='Process directories recursively')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    total_success = 0
    total_error = 0
    
    for input_path in args.input:
        if os.path.isdir(input_path):
            if args.verbose:
                print(f"Processing directory {input_path}...")
            
            success, error = process_directory(input_path, args.output, args.format, args.recursive, args.verbose)
            total_success += success
            total_error += error
        
        elif os.path.isfile(input_path):
            if args.verbose:
                print(f"Processing file {input_path}...")
            
            success, error = process_file(input_path, args.output, args.format, args.verbose)
            
            if success:
                total_success += 1
            else:
                total_error += 1
                if args.verbose:
                    print(error)
        
        else:
            print(f"Error: {input_path} does not exist")
    
    print(f"Processed {total_success + total_error} files: {total_success} successful, {total_error} failed")

if __name__ == "__main__":
    main() 