#!/usr/bin/env python3

import sys
import os
import re
import struct
import argparse
import json
from pathlib import Path

def string_to_binary(string):
    """
    Convert a string to binary format with a 4-byte length prefix.
    
    Args:
        string: String to convert
        
    Returns:
        Binary data as bytes
    """
    # Encode the string as UTF-8
    string_bytes = string.encode('utf-8')
    # Create a 4-byte length prefix (big endian)
    length_bytes = len(string_bytes).to_bytes(4, byteorder='big')
    # Return the combined bytes
    return length_bytes + string_bytes

def parse_text_file(text_file_path, verbose=False):
    """
    Parse a text file and extract metadata and test sequence.
    
    Args:
        text_file_path: Path to the text file
        verbose: Whether to print verbose output
        
    Returns:
        Dictionary containing the extracted data
    """
    with open(text_file_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Extract metadata and test sequence
    metadata = {}
    test_sequence = []
    
    in_test_sequence = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if line == "--- Test Sequence ---":
            in_test_sequence = True
            continue
            
        if not in_test_sequence:
            # Parse metadata
            if ":" in line:
                key, value = line.split(":", 1)
                metadata[key.strip()] = value.strip()
        else:
            # Parse test sequence lines
            test_sequence.append(line)
    
    if verbose:
        print(f"Extracted metadata: {metadata}")
        print(f"Extracted {len(test_sequence)} test sequence commands")
    
    return {
        "metadata": metadata,
        "test_sequence": test_sequence
    }

def parse_json_file(json_file_path, verbose=False):
    """
    Parse a JSON file and extract metadata and test sequence.
    
    Args:
        json_file_path: Path to the JSON file
        verbose: Whether to print verbose output
        
    Returns:
        Dictionary containing the extracted data
    """
    with open(json_file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    if verbose:
        print(f"Loaded JSON data with {len(data.get('test_sequence', []))} test sequence commands")
    
    return data

def text_to_binary(parsed_data, verbose=False):
    """
    Convert parsed text data to binary format.
    
    Args:
        parsed_data: Dictionary containing the parsed data
        verbose: Whether to print verbose output
        
    Returns:
        Binary data as bytes
    """
    metadata = parsed_data.get("metadata", {})
    test_sequence = parsed_data.get("test_sequence", [])
    
    # Create binary data
    binary_data = bytearray()
    
    # Header data (based on reverse engineering from hex dumps)
    # The first bytes appear to be a file identifier or version
    binary_data.extend(b'\x00\x00\x00\x12\x00\x00\x00\x06\x00\x00\x00\x01\x31')
    
    # Add Part Number
    if "Part Number" in metadata:
        binary_data.extend(string_to_binary("Part Number"))
        binary_data.extend(string_to_binary("--"))
        binary_data.extend(string_to_binary(metadata["Part Number"]))
    
    # Add Model Number
    if "Model Number" in metadata:
        binary_data.extend(string_to_binary("Model Number"))
        binary_data.extend(string_to_binary("--"))
        binary_data.extend(string_to_binary(metadata["Model Number"]))
    
    # Add Free Length
    if "Free Length" in metadata:
        free_length = metadata["Free Length"]
        # Extract just the number and unit
        parts = free_length.split()
        value = parts[0]
        unit = "mm"  # Default unit
        if len(parts) > 1:
            unit = parts[1]
        
        binary_data.extend(string_to_binary("Free Length"))
        binary_data.extend(string_to_binary(unit))
        binary_data.extend(string_to_binary(value))
    
    # Add test sequence header
    binary_data.extend(string_to_binary("<Test Sequence>"))
    
    # Determine force unit based on test type (from model number or part number)
    force_unit = "N"
    if "Force Unit" in metadata:
        force_unit = metadata["Force Unit"]
    elif "Model Number" in metadata and any(x in metadata["Model Number"] for x in ["Tens", "Tension"]):
        force_unit = "kgf"
    elif "Part Number" in metadata and any(x in metadata["Part Number"] for x in ["Tens", "Tension"]):
        force_unit = "kgf"
    
    binary_data.extend(string_to_binary(force_unit))
    binary_data.extend(string_to_binary("--"))
    binary_data.extend(string_to_binary("Height"))
    binary_data.extend(string_to_binary("300"))
    binary_data.extend(string_to_binary("800" if force_unit == "kgf" else "100"))
    
    # Process test sequence
    for cmd_line in test_sequence:
        if not cmd_line:
            continue
        
        # Parse the command line
        parts = cmd_line.split(" - ", 1)
        if len(parts) < 2:
            if verbose:
                print(f"Skipping invalid command line: {cmd_line}")
            continue
        
        cmd = parts[0]
        rest = parts[1]
        
        # Process based on command type
        if cmd == "ZF":
            # Zero Force
            binary_data.extend(string_to_binary("ZF"))
            binary_data.extend(string_to_binary(rest))
            # Add padding
            binary_data.extend(b'\x00' * 16)
        
        elif cmd == "ZD":
            # Zero Displacement
            binary_data.extend(string_to_binary("ZD"))
            binary_data.extend(string_to_binary(rest))
            # Add padding
            binary_data.extend(b'\x00' * 16)
        
        elif cmd == "TH":
            # Threshold (Search Contact)
            binary_data.extend(string_to_binary("TH"))
            
            # Parse description and parameters
            if ":" in rest:
                description, params = rest.split(":", 1)
                binary_data.extend(string_to_binary(description.strip()))
                
                # Parse force, unit, and value
                params = params.strip()
                if "," in params:
                    force_part, value_part = params.split(",", 1)
                    force_parts = force_part.strip().split()
                    if len(force_parts) >= 2:
                        force = force_parts[0]
                        unit = force_parts[1]
                        binary_data.extend(string_to_binary(force))
                        binary_data.extend(string_to_binary(unit))
                        
                        # Extract value
                        value = value_part.strip()
                        if value.startswith("Value:"):
                            value = value[6:].strip()
                        binary_data.extend(string_to_binary(value))
                    else:
                        # Fallback if parsing fails
                        binary_data.extend(string_to_binary("10"))
                        binary_data.extend(string_to_binary("N"))
                        binary_data.extend(string_to_binary("10"))
                else:
                    # Fallback if parsing fails
                    binary_data.extend(string_to_binary("10"))
                    binary_data.extend(string_to_binary("N"))
                    binary_data.extend(string_to_binary("10"))
            else:
                # Fallback if parsing fails
                binary_data.extend(string_to_binary("Search Contact"))
                binary_data.extend(string_to_binary("10"))
                binary_data.extend(string_to_binary("N"))
                binary_data.extend(string_to_binary("10"))
        
        elif cmd == "FL(P)":
            # Measure Free Length
            binary_data.extend(string_to_binary("FL(P)"))
            
            # Parse description and parameters
            if ":" in rest:
                description, params = rest.split(":", 1)
                binary_data.extend(string_to_binary(description.strip()))
                
                # Parse unit and value
                params = params.strip()
                if "(" in params and ")" in params:
                    # Format like "50(40,60)"
                    binary_data.extend(string_to_binary("mm"))
                    binary_data.extend(string_to_binary(params))
                else:
                    # Default values
                    binary_data.extend(string_to_binary("mm"))
                    binary_data.extend(string_to_binary(params))
            else:
                # Fallback if parsing fails
                binary_data.extend(string_to_binary("Measure Free Length"))
                binary_data.extend(string_to_binary("mm"))
                binary_data.extend(string_to_binary("50"))
        
        elif cmd == "Mv(P)":
            # Move to Position
            binary_data.extend(string_to_binary("Mv(P)"))
            
            # Parse description and parameters
            if ":" in rest:
                description, params = rest.split(":", 1)
                binary_data.extend(string_to_binary(description.strip()))
                
                # Parse position, unit, and target
                params = params.strip()
                if "," in params:
                    position_part, target_part = params.split(",", 1)
                    position_parts = position_part.strip().split()
                    
                    if len(position_parts) >= 2:
                        position = position_parts[0]
                        unit = position_parts[1]
                        binary_data.extend(string_to_binary(position))
                        binary_data.extend(string_to_binary(unit))
                    else:
                        # Position without unit
                        binary_data.extend(string_to_binary(position_part.strip()))
                        binary_data.extend(string_to_binary("mm"))
                    
                    # Extract target
                    target = target_part.strip()
                    if target.startswith("Target:"):
                        target = target[7:].strip()
                    binary_data.extend(string_to_binary(target))
                else:
                    # No target specified
                    binary_data.extend(string_to_binary(params))
                    binary_data.extend(string_to_binary("mm"))
                    binary_data.extend(string_to_binary("50"))
            else:
                # Fallback if parsing fails
                binary_data.extend(string_to_binary("Move to Position"))
                binary_data.extend(string_to_binary("50"))
                binary_data.extend(string_to_binary("mm"))
                binary_data.extend(string_to_binary("50"))
        
        elif cmd == "Fr(P)":
            # Force at Position
            binary_data.extend(string_to_binary("Fr(P)"))
            
            # Parse description and parameters
            if ":" in rest:
                description, params = rest.split(":", 1)
                binary_data.extend(string_to_binary(description.strip()))
                
                # Add unit and value
                binary_data.extend(string_to_binary("N"))
                binary_data.extend(string_to_binary(params.strip()))
            else:
                # Fallback if parsing fails
                binary_data.extend(string_to_binary("Force at Position"))
                binary_data.extend(string_to_binary("N"))
                binary_data.extend(string_to_binary("100"))
        
        elif cmd == "TD":
            # Time Delay
            binary_data.extend(string_to_binary("TD"))
            
            # Parse description and parameters
            if ":" in rest:
                description, params = rest.split(":", 1)
                binary_data.extend(string_to_binary(description.strip()))
                
                # Parse time and unit
                params = params.strip().split()
                if len(params) >= 2:
                    time = params[0]
                    unit = params[1]
                    binary_data.extend(string_to_binary(time))
                    binary_data.extend(string_to_binary(unit))
                else:
                    # Default values
                    binary_data.extend(string_to_binary("1"))
                    binary_data.extend(string_to_binary("Sec"))
            else:
                # Fallback if parsing fails
                binary_data.extend(string_to_binary("Time Delay"))
                binary_data.extend(string_to_binary("1"))
                binary_data.extend(string_to_binary("Sec"))
        
        elif cmd == "Scrag":
            # Scragging
            binary_data.extend(string_to_binary("Scrag"))
            
            # Parse description and parameters
            if ":" in rest:
                description, params = rest.split(":", 1)
                binary_data.extend(string_to_binary(description.strip()))
                binary_data.extend(string_to_binary(params.strip()))
            else:
                # Fallback if parsing fails
                binary_data.extend(string_to_binary("Scragging"))
                binary_data.extend(string_to_binary("R03,2"))
            
            # Add padding
            binary_data.extend(b'\x00' * 16)
        
        elif cmd == "PMsg":
            # User Message
            binary_data.extend(string_to_binary("PMsg"))
            
            # Parse description and parameters
            if ":" in rest:
                description, params = rest.split(":", 1)
                binary_data.extend(string_to_binary(description.strip()))
                binary_data.extend(string_to_binary(params.strip()))
            else:
                # Fallback if parsing fails
                binary_data.extend(string_to_binary("User Message"))
                binary_data.extend(string_to_binary("Test Completed"))
            
            # Add padding
            binary_data.extend(b'\x00' * 16)
        
        elif cmd == "LP":
            # Loop
            binary_data.extend(string_to_binary("LP"))
            
            # Parse description and parameters
            if ":" in rest:
                description, params = rest.split(":", 1)
                binary_data.extend(string_to_binary(description.strip()))
                binary_data.extend(string_to_binary(params.strip()))
            else:
                # Fallback if parsing fails
                binary_data.extend(string_to_binary("Loop"))
                binary_data.extend(string_to_binary("R03,3"))
            
            # Add padding
            binary_data.extend(b'\x00' * 16)
        
        else:
            # Unknown command, try to add it as-is
            if verbose:
                print(f"Warning: Unknown command '{cmd}' - adding as-is")
            
            binary_data.extend(string_to_binary(cmd))
            binary_data.extend(string_to_binary(rest))
    
    return binary_data

def process_file(input_file, output_dir=None, verbose=False):
    """
    Process a single text file and convert it to binary format.
    
    Args:
        input_file: Path to the input text file
        output_dir: Directory to save output files
        verbose: Whether to print verbose output
        
    Returns:
        Tuple of (success, error_message)
    """
    try:
        input_path = Path(input_file)
        
        # Determine input file type
        is_json = input_path.suffix.lower() == '.json'
        
        # Parse the input file
        if is_json:
            parsed_data = parse_json_file(input_file, verbose)
        else:
            parsed_data = parse_text_file(input_file, verbose)
        
        # Determine output directory
        if output_dir:
            output_dir = Path(output_dir)
        else:
            output_dir = input_path.parent / "input"
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate output file name
        base_name = input_path.stem
        if '_' in base_name:
            # Convert AS_01_Comp-Deflection.txt to AS 01~Comp-Deflection
            parts = base_name.split('_', 2)
            if len(parts) >= 3:
                output_name = f"{parts[0]} {parts[1]}~{parts[2]}"
            else:
                output_name = base_name.replace('_', ' ', 1).replace('_', '~', 1)
        else:
            output_name = base_name
        
        binary_output_path = output_dir / output_name
        hex_output_path = output_dir / f"{output_name}_hex_dump.txt"
        
        # Convert to binary
        binary_data = text_to_binary(parsed_data, verbose)
        
        # Write binary output
        with open(binary_output_path, 'wb') as f:
            f.write(binary_data)
        
        # Create hex dump for verification
        from encoder import create_hex_dump
        hex_dump = create_hex_dump(binary_data)
        with open(hex_output_path, 'w', encoding='utf-8') as f:
            f.write(hex_dump)
        
        if verbose:
            print(f"Successfully converted '{input_file}' to binary")
            print(f"- Binary output: '{binary_output_path}'")
            print(f"- Hex dump: '{hex_output_path}'")
        
        return True, ""
    
    except Exception as e:
        error_message = f"Error processing file {input_file}: {str(e)}"
        if verbose:
            print(error_message)
            import traceback
            traceback.print_exc()
        return False, error_message

def process_directory(input_dir, output_dir, recursive=False, verbose=False):
    """
    Process all text files in a directory.
    
    Args:
        input_dir: Directory containing input text files
        output_dir: Directory to save output files
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
                if filename.endswith('.txt') or filename.endswith('.json'):
                    files.append(os.path.join(root, filename))
    else:
        files = [os.path.join(input_dir, f) for f in os.listdir(input_dir) 
                if os.path.isfile(os.path.join(input_dir, f)) 
                and (f.endswith('.txt') or f.endswith('.json'))]
    
    # Process each file
    for file_path in files:
        if verbose:
            print(f"Processing {file_path}...")
        
        success, error = process_file(file_path, output_dir, verbose)
        
        if success:
            success_count += 1
        else:
            error_count += 1
            if verbose:
                print(error)
    
    return success_count, error_count

def main():
    parser = argparse.ArgumentParser(description='Convert text spring force test files back to binary format.')
    parser.add_argument('input', nargs='+', help='Input text files or directories')
    parser.add_argument('-o', '--output', help='Output directory for converted binary files')
    parser.add_argument('-r', '--recursive', action='store_true', help='Process directories recursively')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose output')
    
    args = parser.parse_args()
    
    total_success = 0
    total_error = 0
    
    for input_path in args.input:
        if os.path.isdir(input_path):
            if args.verbose:
                print(f"Processing directory {input_path}...")
            
            success, error = process_directory(input_path, args.output, args.recursive, args.verbose)
            total_success += success
            total_error += error
        
        elif os.path.isfile(input_path):
            if args.verbose:
                print(f"Processing file {input_path}...")
            
            success, error = process_file(input_path, args.output, args.verbose)
            
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