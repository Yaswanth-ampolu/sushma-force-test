#!/usr/bin/env python3

import sys
import os
import re
import json
import struct
import argparse
from pathlib import Path

def parse_binary_file(file_path):
    """
    Parse a binary test procedure file with length-prefixed strings.

    Args:
        file_path: Path to the binary file

    Returns:
        Structured dictionary of the file content
    """
    with open(file_path, 'rb') as f:
        data = f.read()

    # First pass: identify string locations and lengths
    strings = []
    i = 0
    while i < len(data):
        # Look for pattern: 4-byte length followed by string data
        if i + 4 <= len(data):
            str_len = int.from_bytes(data[i:i+4], byteorder='big')
            # Arbitrary upper bound (change as needed)
            if 0 < str_len < 100 and i + 4 + str_len <= len(data):
                try:
                    # Decode string as UTF-8, replacing errors
                    string_data = data[i+4:i+4+str_len].decode('utf-8', errors='replace')
                    # Collect it
                    strings.append((i, str_len, string_data))
                except:
                    pass
        i += 1

    # Build a structured representation
    result = {}

    # Look for metadata patterns
    part_number = extract_pattern(strings, r'Part Number')
    model_number = extract_pattern(strings, r'Model Number')
    free_length = extract_pattern(strings, r'Free Length')

    # If "Part Number" appears, grab the next value after "--"
    if part_number:
        for i, (pos, _, s) in enumerate(strings):
            if s == "Part Number" and i+2 < len(strings):
                if strings[i+1][2] == "--":
                    result["Part Number"] = strings[i+2][2]
                    break

    # If "Model Number" appears, grab the next value after "--"
    if model_number:
        for i, (pos, _, s) in enumerate(strings):
            if s == "Model Number" and i+2 < len(strings):
                if strings[i+1][2] == "--":
                    result["Model Number"] = strings[i+2][2]
                    break

    # If "Free Length" appears, grab the next value after "mm"
    if free_length:
        for i, (pos, _, s) in enumerate(strings):
            if s == "Free Length" and i+2 < len(strings):
                if strings[i+1][2] == "mm":
                    result["Free Length"] = f"{strings[i+2][2]} mm"
                    break

    # Extract test sequence
    test_sequence = []
    in_sequence = False

    for i, (pos, _, s) in enumerate(strings):
        if s == "<Test Sequence>":
            in_sequence = True
            continue

        if in_sequence:
            # Various test steps
            if s == "ZF" and i+1 < len(strings) and strings[i+1][2] == "Zero Force":
                test_sequence.append({"step": "Zero Force", "command": "ZF"})

            elif s == "TH" and i+3 < len(strings) and strings[i+1][2] == "Search Contact":
                force = strings[i+2][2] if i+2 < len(strings) else "?"
                value = strings[i+4][2] if i+4 < len(strings) else "?"
                test_sequence.append({
                    "step": "Search Contact",
                    "command": "TH",
                    "force": f"{force} N",
                    "value": value
                })

            elif s == "FL(P)" and i+4 < len(strings):
                desc = strings[i+1][2] if i+1 < len(strings) else "?"
                unit = strings[i+3][2] if i+3 < len(strings) else "?"
                value = strings[i+4][2] if i+4 < len(strings) else "?"
                test_sequence.append({
                    "step": desc,
                    "command": "FL(P)",
                    "value": f"{value} {unit}"
                })

            elif s == "Mv(P)" and i+4 < len(strings) and strings[i+1][2] == "Move to Position":
                pos_val = strings[i+2][2] if i+2 < len(strings) else "?"
                unit = strings[i+3][2] if i+3 < len(strings) else "?"
                target = strings[i+4][2] if i+4 < len(strings) else "?"
                test_sequence.append({
                    "step": "Move to Position",
                    "command": "Mv(P)",
                    "position": f"{pos_val} {unit}",
                    "target": target
                })

            elif s == "Scrag" and i+2 < len(strings) and strings[i+1][2] == "Scragging":
                params = strings[i+2][2] if i+2 < len(strings) else "?"
                test_sequence.append({
                    "step": "Scragging",
                    "command": "Scrag",
                    "params": params
                })

            elif s == "Fr(P)" and i+3 < len(strings):
                params = strings[i+3][2] if i+3 < len(strings) else "?"
                test_sequence.append({
                    "step": "Force at Position",
                    "command": "Fr(P)",
                    "value": params
                })

            elif s == "TD" and i+2 < len(strings) and strings[i+1][2] == "Time Delay":
                time = strings[i+2][2] if i+2 < len(strings) else "?"
                unit = strings[i+3][2] if i+3 < len(strings) else "?"
                test_sequence.append({
                    "step": "Time Delay",
                    "command": "TD",
                    "duration": f"{time} {unit}"
                })

            elif s == "PMsg" and i+2 < len(strings) and strings[i+1][2] == "User Message":
                msg = strings[i+2][2] if i+2 < len(strings) else "?"
                test_sequence.append({
                    "step": "User Message",
                    "command": "PMsg",
                    "message": msg
                })

    result["Test Sequence"] = test_sequence
    return result

def extract_pattern(strings, pattern):
    """Extract strings matching a pattern."""
    return [s for _, _, s in strings if re.search(pattern, s, re.IGNORECASE)]

def format_as_text(parsed_data):
    """
    Format the parsed data as readable text.
    """
    lines = []

    # Metadata
    if "Part Number" in parsed_data:
        lines.append(f"Part Number: {parsed_data['Part Number']}")

    if "Model Number" in parsed_data:
        lines.append(f"Model Number: {parsed_data['Model Number']}")

    if "Free Length" in parsed_data:
        lines.append(f"Free Length: {parsed_data['Free Length']}")

    lines.append("")
    lines.append("--- Test Sequence ---")

    # Test sequence
    for step in parsed_data.get("Test Sequence", []):
        cmd = step.get("command", "?")
        if cmd == "ZF":
            lines.append(f"ZF - Zero Force")

        elif cmd == "TH":
            lines.append(f"TH - Search Contact: {step.get('force', '?')}, Value: {step.get('value', '?')}")

        elif cmd == "FL(P)":
            lines.append(f"FL(P) - {step.get('step', 'Measure')}: {step.get('value', '?')}")

        elif cmd == "Mv(P)":
            lines.append(f"Mv(P) - Move to Position: {step.get('position', '?')}, Target: {step.get('target', '?')}")

        elif cmd == "Scrag":
            lines.append(f"Scrag - Scragging: {step.get('params', '?')}")

        elif cmd == "Fr(P)":
            lines.append(f"Fr(P) - Force at Position: {step.get('value', '?')}")

        elif cmd == "TD":
            lines.append(f"TD - Time Delay: {step.get('duration', '?')}")

        elif cmd == "PMsg":
            lines.append(f"PMsg - User Message: {step.get('message', '?')}")

        else:
            # Generic fallback if we find something unrecognized
            lines.append(f"{cmd} - {step.get('step', '?')}")

    return "\n".join(lines)

def create_hex_dump(binary_data, bytes_per_line=16):
    """
    Creates a hexadecimal representation of binary data for inspection.
    """
    result = []
    ascii_repr = []

    for i, byte in enumerate(binary_data):
        # Add offset at the beginning of each line
        if i % bytes_per_line == 0:
            if i > 0:
                # Add ASCII representation
                result.append("  " + "".join(ascii_repr))
                result.append("\n")
                ascii_repr = []
            result.append(f"{i:08x}:  ")

        # Add hex representation
        result.append(f"{byte:02x} ")

        # Add to ASCII representation (for the right-hand column)
        if 32 <= byte <= 126:  # Printable ASCII characters
            ascii_repr.append(chr(byte))
        else:
            ascii_repr.append(".")

    # Add padding for the last line if needed
    padding = bytes_per_line - (len(binary_data) % bytes_per_line) if len(binary_data) % bytes_per_line != 0 else 0
    result.append("   " * padding)

    # Add the last ASCII representation
    result.append("  " + "".join(ascii_repr))

    return "".join(result)

def process_file(input_file, output_dir=None, output_format='txt'):
    """
    Process a single binary file and convert it to readable formats.
    - Creates a hex dump in 'encoder' subfolder
    - Creates text/json in the main 'output_dir'
    """
    input_path = Path(input_file)

    # Check if file exists
    if not input_path.exists():
        print(f"Error: Input file '{input_file}' not found")
        return

    # If user specified an output directory, use that
    if output_dir:
        output_dir = Path(output_dir)
    else:
        # Default to a new 'output' folder where the input file is
        output_dir = input_path.parent / "output"

    # Make sure the main output folder exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Subfolder for encoded data (hex dumps)
    encoder_dir = output_dir / "encoder"
    encoder_dir.mkdir(parents=True, exist_ok=True)

    # Base name for output files
    base_name = input_path.stem.replace('~', '_').replace(' ', '_')

    # 1) Create hex dump (goes in encoder folder)
    with open(input_path, 'rb') as f:
        binary_data = f.read()

    hex_dump = create_hex_dump(binary_data)
    hex_output_path = encoder_dir / f"{base_name}_hex_dump.txt"
    with open(hex_output_path, 'w', encoding='utf-8') as f:
        f.write(hex_dump)

    # 2) Parse the file
    try:
        parsed_data = parse_binary_file(input_path)

        # -- Save as text
        text_output = format_as_text(parsed_data)
        txt_output_path = output_dir / f"{base_name}.txt"
        with open(txt_output_path, 'w', encoding='utf-8') as f:
            f.write(text_output)

        # -- Save as JSON if requested
        if output_format in ['json', 'all']:
            json_output_path = output_dir / f"{base_name}.json"
            with open(json_output_path, 'w', encoding='utf-8') as f:
                json.dump(parsed_data, f, indent=2)

        print(f"Successfully converted '{input_file}':")
        print(f"- Text output: '{txt_output_path}'")
        print(f"- Hex dump: '{hex_output_path}'")
        if output_format in ['json', 'all']:
            print(f"- JSON output: '{json_output_path}'")

    except Exception as e:
        print(f"Error processing '{input_file}': {str(e)}")
        # Still save the hex dump
        print(f"- Hex dump (only): '{hex_output_path}'")

def main():
    parser = argparse.ArgumentParser(description='Convert binary test files to readable formats.')
    parser.add_argument('input_paths', nargs='+', help='Input file(s) or directory to convert')
    parser.add_argument('-o', '--output', help='Output directory for converted files')
    parser.add_argument('-f', '--format', choices=['txt', 'json', 'all'], default='txt',
                        help='Output format (default: txt)')
    parser.add_argument('-r', '--recursive', action='store_true', help='Process directories recursively')

    args = parser.parse_args()

    # Process each input path
    for input_path in args.input_paths:
        path = Path(input_path)

        if path.is_file():
            # Process a single file
            process_file(path, args.output, args.format)

        elif path.is_dir():
            # Process a directory
            if args.recursive:
                # Walk through all subdirectories
                for root, _, files in os.walk(path):
                    for file in files:
                        file_path = Path(root) / file
                        # Skip already processed files
                        if file_path.suffix.lower() in ['.txt', '.json']:
                            continue
                        process_file(file_path, args.output, args.format)
            else:
                # Process only files in the top directory
                for file in path.iterdir():
                    if file.is_file() and file.suffix.lower() not in ['.txt', '.json']:
                        process_file(file, args.output, args.format)

        else:
            print(f"Error: '{input_path}' is not a valid file or directory")

if __name__ == "__main__":
    main()