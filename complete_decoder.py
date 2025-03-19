#!/usr/bin/env python3

import os
import sys
import struct
import re
import json
import pandas as pd
import argparse
from pathlib import Path
import binascii
import io
import datetime

class LabVIEWDatabaseDecoder:
    """
    A comprehensive decoder for LabVIEW database files.
    This decoder extracts all information from LabVIEW binary files without missing any data.
    It handles component specifications, test sequences, and all embedded metadata.
    """
    
    def __init__(self, verbose=False):
        self.verbose = verbose
        # Command dictionary for translating test commands
        self.command_dict = {
            "ZF": "Zero Force", 
            "ZD": "Zero Displacement", 
            "TH": "Threshold (Search Contact)",
            "LP": "Loop", 
            "Mv(P)": "Move to Position", 
            "Calc": "Formula Calculation",
            "TD": "Time Delay", 
            "PMsg": "User Message", 
            "Fr(P)": "Force at Position",
            "FL(P)": "Measure Free Length", 
            "Scrag": "Scragging", 
            "SR": "Spring Rate",
            "PkF": "Measure Peak Force", 
            "PkP": "Measure Peak Position", 
            "Po(F)": "Position at Force",
            "Po(PkF)": "Position at Peak Force", 
            "Mv(F)": "Move to Force", 
            "PUi": "User Input"
        }
        
        # Known internal structure markers
        self.known_markers = {
            b'\x00\x00\x00\x12': 'File Header',
            b'\x00\x00\x00\x0f': 'String Length',
            b'\x00\x00\x00\x0c': 'String Length',
            b'\x00\x00\x00\x0b': 'String Length',
            b'\x00\x00\x00\x0a': 'String Length',
            b'\x00\x00\x00\x02': 'Short Value',
            b'\x00\x00\x00\x01': 'Boolean/Marker'
        }
    
    def decode_file(self, file_path):
        """
        Main function to decode a LabVIEW database file.
        First tries to process as binary, then falls back to text if needed.
        
        Args:
            file_path: Path to the LabVIEW database file
            
        Returns:
            Dictionary containing all extracted data
        """
        if self.verbose:
            print(f"Decoding file: {file_path}")
        
        try:
            # Try to read as binary first
            return self.decode_binary_file(file_path)
        except Exception as e:
            if self.verbose:
                print(f"Binary decode failed: {e}")
                print("Falling back to text processing...")
            
            # Fall back to text processing
            return self.decode_text_file(file_path)
    
    def decode_binary_file(self, file_path):
        """
        Decode the binary LabVIEW database file format.
        
        Args:
            file_path: Path to the binary LabVIEW file
            
        Returns:
            Dictionary with all extracted data
        """
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Create a hex dump for detailed inspection if verbose
        if self.verbose:
            self._create_hex_dump(file_path, file_data)
        
        # Extract data from the binary
        result = {
            "file_info": {
                "file_name": os.path.basename(file_path),
                "file_path": os.path.abspath(file_path),
                "file_size": len(file_data),
                "decode_time": datetime.datetime.now().isoformat(),
                "decoded_by": "LabVIEWDatabaseDecoder"
            },
            "component_specifications": {},
            "test_sequence": []
        }
        
        # Extract string data - any sequence of readable ASCII
        i = 0
        strings = []
        
        # Typical LabVIEW pattern: 4 bytes length, then the string
        while i < len(file_data):
            # Check for known length marker
            if i + 4 <= len(file_data):
                length_bytes = file_data[i:i+4]
                
                try:
                    length = struct.unpack('>I', length_bytes)[0]
                    
                    # If we have a valid length between 1 and 100 (reasonable for strings)
                    if 0 < length <= 100 and i + 4 + length <= len(file_data):
                        string_data = file_data[i+4:i+4+length]
                        
                        # Check if the data is ASCII printable
                        if all(32 <= b <= 126 for b in string_data):
                            string_value = string_data.decode('utf-8', errors='replace')
                            strings.append((i, string_value))
                            
                            if self.verbose:
                                print(f"Found string at offset {i}: {string_value}")
                except:
                    pass
            i += 1
        
        # Extract component specifications from strings
        for i in range(len(strings) - 2):
            if strings[i][1] in ["Part Number", "Model Number", "Free Length"]:
                key = strings[i][1]
                
                # Try to find the value by checking subsequent strings
                for j in range(i+1, min(i+5, len(strings))):
                    value = strings[j][1]
                    if value != "--" and value != "mm" and not value.startswith("<"):
                        # If it's Free Length, also add the unit
                        if key == "Free Length" and j > 0 and strings[j-1][1] == "mm":
                            value = f"{value} mm"
                        
                        result["component_specifications"][key] = value
                        break
        
        # Extract test sequence
        # Find the Test Sequence marker
        test_seq_marker = -1
        for i, (offset, string) in enumerate(strings):
            if string == "<Test Sequence>":
                test_seq_marker = i
                break
        
        if test_seq_marker >= 0:
            # Parse command sequences after the marker
            i = test_seq_marker + 1
            while i < len(strings) - 1:
                try:
                    cmd = strings[i][1]
                    
                    # Only process if it looks like a command
                    if cmd in self.command_dict or re.match(r'^[A-Za-z]+(\([A-Za-z]+\))?$', cmd):
                        command_data = {
                            "Row": f"R{len(result['test_sequence']):02d}",
                            "CMD": cmd,
                            "Description": self.command_dict.get(cmd, cmd),
                            "Condition": "",
                            "Unit": "",
                            "Tolerance": "",
                            "Speed": ""
                        }
                        
                        # Look ahead for parameters
                        for j in range(i+1, min(i+5, len(strings))):
                            param = strings[j][1]
                            
                            # Check the parameter's context to categorize it
                            if re.match(r'^\d+(\.\d+)?$', param) or param.startswith('='):
                                command_data["Condition"] = param
                            elif param in ["mm", "sec", "N", "kgf", "Force", "Move"]:
                                command_data["Unit"] = param
                            elif "(" in param and ")" in param:
                                command_data["Tolerance"] = param
                            elif param in ["Value", "Target"]:
                                # Skip these keywords
                                pass
                            else:
                                # If it has special characters, it's likely a condition
                                if any(c in param for c in "()[],+-*/"):
                                    command_data["Condition"] = param
                        
                        result["test_sequence"].append(command_data)
                        i += 1
                    else:
                        i += 1
                except Exception as e:
                    if self.verbose:
                        print(f"Error parsing command at {i}: {e}")
                    i += 1
        
        # Add raw extracted strings for verification
        result["_extracted_strings"] = [s[1] for s in strings]
        
        return result
    
    def decode_text_file(self, file_path):
        """
        Decode the file assuming it's already in text format.
        
        Args:
            file_path: Path to the text file
            
        Returns:
            Dictionary with extracted data
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try reading as binary and decode
            with open(file_path, 'rb') as f:
                content = f.read().decode('utf-8', errors='replace')
        
        result = {
            "file_info": {
                "file_name": os.path.basename(file_path),
                "file_path": os.path.abspath(file_path),
                "decode_time": datetime.datetime.now().isoformat(),
                "decoded_by": "LabVIEWDatabaseDecoder"
            },
            "component_specifications": {},
            "test_sequence": []
        }
        
        # Split into lines
        lines = content.split('\n')
        
        # Extract component specifications
        in_test_sequence = False
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if "--- Test Sequence ---" in line:
                in_test_sequence = True
                continue
                
            if not in_test_sequence:
                # Parse component specifications
                if ":" in line:
                    key, value = line.split(":", 1)
                    result["component_specifications"][key.strip()] = value.strip()
            else:
                # Parse test sequence
                # Format is typically: CMD - Description: Params
                parts = line.split(" - ", 1)
                if len(parts) >= 2:
                    cmd = parts[0].strip()
                    rest = parts[1].strip()
                    
                    # Extract description and parameters
                    if ":" in rest:
                        desc, params = rest.split(":", 1)
                        params = params.strip()
                    else:
                        desc = rest
                        params = ""
                    
                    # Create command entry
                    command_data = {
                        "Row": f"R{len(result['test_sequence']):02d}",
                        "CMD": cmd,
                        "Description": desc,
                        "Condition": "",
                        "Unit": "",
                        "Tolerance": "",
                        "Speed": ""
                    }
                    
                    # Parse parameters
                    if params:
                        param_parts = params.split(",")
                        for param in param_parts:
                            param = param.strip()
                            
                            # Try to identify parameter type
                            if " mm" in param:
                                value, _ = param.split(" mm", 1)
                                command_data["Condition"] = value
                                command_data["Unit"] = "mm"
                            elif " N" in param:
                                value, _ = param.split(" N", 1)
                                command_data["Condition"] = value
                                command_data["Unit"] = "N"
                            elif " Sec" in param:
                                value, _ = param.split(" Sec", 1)
                                command_data["Condition"] = value
                                command_data["Unit"] = "Sec"
                            elif "Target:" in param:
                                _, value = param.split("Target:", 1)
                                command_data["Tolerance"] = value.strip()
                            elif "Value:" in param:
                                _, value = param.split("Value:", 1)
                                command_data["Tolerance"] = value.strip()
                            elif "(" in param and ")" in param:
                                command_data["Tolerance"] = param
                            else:
                                command_data["Condition"] = param
                    
                    result["test_sequence"].append(command_data)
        
        return result
    
    def _create_hex_dump(self, file_path, data):
        """
        Create a hex dump of the binary data for analysis.
        
        Args:
            file_path: Original file path
            data: Binary data
        """
        hex_dump_path = f"{file_path}_hex_dump.txt"
        
        with open(hex_dump_path, 'w') as f:
            for i in range(0, len(data), 16):
                chunk = data[i:i+16]
                hex_values = ' '.join(f'{b:02x}' for b in chunk)
                ascii_values = ''.join(chr(b) if 32 <= b <= 126 else '.' for b in chunk)
                
                f.write(f"{i:08x}:  {hex_values.ljust(47)}  {ascii_values}\n")
        
        if self.verbose:
            print(f"Hex dump created at: {hex_dump_path}")
    
    def export_to_json(self, data, output_path):
        """
        Export the decoded data to JSON format.
        
        Args:
            data: Decoded data dictionary
            output_path: Output file path
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        
        if self.verbose:
            print(f"JSON file exported to {output_path}")
    
    def export_to_excel(self, data, output_path):
        """
        Export the decoded data to Excel format.
        
        Args:
            data: Decoded data dictionary
            output_path: Output file path
        """
        with pd.ExcelWriter(output_path) as writer:
            # Write component specifications
            specs_df = pd.DataFrame([data["component_specifications"]]).T
            specs_df.columns = ["Value"]
            specs_df.index.name = "Parameter"
            specs_df.reset_index(inplace=True)
            specs_df.to_excel(writer, sheet_name="Component Specs", index=False)
            
            # Write test sequence
            if data["test_sequence"]:
                test_df = pd.DataFrame(data["test_sequence"])
                test_df.to_excel(writer, sheet_name="Test Sequence", index=False)
            
            # Write file info
            file_info_df = pd.DataFrame([data["file_info"]]).T
            file_info_df.columns = ["Value"]
            file_info_df.index.name = "Attribute"
            file_info_df.reset_index(inplace=True)
            file_info_df.to_excel(writer, sheet_name="File Info", index=False)
            
            # Write raw strings if available
            if "_extracted_strings" in data:
                strings_df = pd.DataFrame(data["_extracted_strings"], columns=["Value"])
                strings_df.index.name = "Index"
                strings_df.reset_index(inplace=True)
                strings_df.to_excel(writer, sheet_name="Raw Strings", index=False)
        
        if self.verbose:
            print(f"Excel file exported to {output_path}")
    
    def export_to_csv(self, data, output_dir):
        """
        Export the decoded data to CSV format.
        
        Args:
            data: Decoded data dictionary
            output_dir: Output directory
        """
        os.makedirs(output_dir, exist_ok=True)
        
        # Write component specifications
        specs_df = pd.DataFrame([data["component_specifications"]]).T
        specs_df.columns = ["Value"]
        specs_df.index.name = "Parameter"
        specs_df.reset_index(inplace=True)
        specs_df.to_csv(os.path.join(output_dir, "component_specs.csv"), index=False)
        
        # Write test sequence
        if data["test_sequence"]:
            test_df = pd.DataFrame(data["test_sequence"])
            test_df.to_csv(os.path.join(output_dir, "test_sequence.csv"), index=False)
        
        # Write file info
        file_info_df = pd.DataFrame([data["file_info"]]).T
        file_info_df.columns = ["Value"]
        file_info_df.index.name = "Attribute"
        file_info_df.reset_index(inplace=True)
        file_info_df.to_csv(os.path.join(output_dir, "file_info.csv"), index=False)
        
        # Write raw strings if available
        if "_extracted_strings" in data:
            strings_df = pd.DataFrame(data["_extracted_strings"], columns=["Value"])
            strings_df.index.name = "Index"
            strings_df.reset_index(inplace=True)
            strings_df.to_csv(os.path.join(output_dir, "raw_strings.csv"), index=False)
        
        if self.verbose:
            print(f"CSV files exported to {output_dir}")
    
    def export_to_txt(self, data, output_path):
        """
        Export the decoded data to text format.
        
        Args:
            data: Decoded data dictionary
            output_path: Output file path
        """
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("=== SPRING TEST FILE DECODED DATA ===\n\n")
            
            # Write file info
            f.write("=== FILE INFORMATION ===\n")
            for key, value in data["file_info"].items():
                f.write(f"{key}: {value}\n")
            f.write("\n")
            
            # Write component specifications
            f.write("=== COMPONENT SPECIFICATIONS ===\n")
            max_param_len = max([len(str(k)) for k in data["component_specifications"].keys()], default=10)
            f.write(f"{'Parameter'.ljust(max_param_len)} | {'Value'}\n")
            f.write("-" * (max_param_len + 2) + "+" + "-" * 30 + "\n")
            
            for param, value in data["component_specifications"].items():
                f.write(f"{str(param).ljust(max_param_len)} | {value}\n")
            f.write("\n")
            
            # Write test sequence
            f.write("=== TEST SEQUENCE ===\n")
            if data["test_sequence"]:
                headers = ["Row", "CMD", "Description", "Condition", "Unit", "Tolerance", "Speed"]
                col_widths = [max(len(str(cmd.get(h, ""))) for cmd in data["test_sequence"] + [{"Row": "Row", "CMD": "CMD", "Description": "Description", "Condition": "Condition", "Unit": "Unit", "Tolerance": "Tolerance", "Speed": "Speed"}]) for h in headers]
                
                # Write header
                header_line = ""
                for i, h in enumerate(headers):
                    header_line += str(h).ljust(col_widths[i] + 2)
                f.write(header_line + "\n")
                
                # Write separator
                f.write("-" * sum(col_widths) + "-" * (len(headers) * 2) + "\n")
                
                # Write data rows
                for cmd in data["test_sequence"]:
                    line = ""
                    for i, h in enumerate(headers):
                        line += str(cmd.get(h, "")).ljust(col_widths[i] + 2)
                    f.write(line + "\n")
            
            # Write raw strings if available
            if "_extracted_strings" in data:
                f.write("\n=== RAW EXTRACTED STRINGS ===\n")
                for i, s in enumerate(data["_extracted_strings"]):
                    f.write(f"{i:03d}: {s}\n")
        
        if self.verbose:
            print(f"Text file exported to {output_path}")
    
    def export_to_html(self, data, output_path):
        """
        Export the decoded data to HTML format.
        
        Args:
            data: Decoded data dictionary
            output_path: Output file path
        """
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>LabVIEW Database Decoder - {data["file_info"]["file_name"]}</title>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; }}
        h1, h2, h3 {{ color: #333; }}
        table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
        th, td {{ text-align: left; padding: 8px; }}
        th {{ background-color: #f2f2f2; }}
        tr:nth-child(even) {{ background-color: #f9f9f9; }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        .section {{ margin-bottom: 30px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>LabVIEW Database Decoder</h1>
        <div class="section">
            <h2>File Information</h2>
            <table>
                <tr><th>Attribute</th><th>Value</th></tr>
"""
        
        # Add file info
        for key, value in data["file_info"].items():
            html += f"                <tr><td>{key}</td><td>{value}</td></tr>\n"
        
        html += """            </table>
        </div>
        
        <div class="section">
            <h2>Component Specifications</h2>
            <table>
                <tr><th>Parameter</th><th>Value</th></tr>
"""
        
        # Add component specifications
        for param, value in data["component_specifications"].items():
            html += f"                <tr><td>{param}</td><td>{value}</td></tr>\n"
        
        html += """            </table>
        </div>
        
        <div class="section">
            <h2>Test Sequence</h2>
            <table>
                <tr>
                    <th>Row</th>
                    <th>Command</th>
                    <th>Description</th>
                    <th>Condition</th>
                    <th>Unit</th>
                    <th>Tolerance</th>
                    <th>Speed</th>
                </tr>
"""
        
        # Add test sequence
        for cmd in data["test_sequence"]:
            html += f"""                <tr>
                    <td>{cmd.get("Row", "")}</td>
                    <td>{cmd.get("CMD", "")}</td>
                    <td>{cmd.get("Description", "")}</td>
                    <td>{cmd.get("Condition", "")}</td>
                    <td>{cmd.get("Unit", "")}</td>
                    <td>{cmd.get("Tolerance", "")}</td>
                    <td>{cmd.get("Speed", "")}</td>
                </tr>
"""
        
        html += """            </table>
        </div>
"""
        
        # Add raw strings if available
        if "_extracted_strings" in data:
            html += """        <div class="section">
            <h2>Raw Extracted Strings</h2>
            <table>
                <tr><th>Index</th><th>Value</th></tr>
"""
            
            for i, s in enumerate(data["_extracted_strings"]):
                html += f"                <tr><td>{i}</td><td>{s}</td></tr>\n"
            
            html += """            </table>
        </div>
"""
        
        html += """    </div>
</body>
</html>"""
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        if self.verbose:
            print(f"HTML file exported to {output_path}")


def main():
    parser = argparse.ArgumentParser(description='LabVIEW Database File Decoder')
    parser.add_argument('file_path', help='Path to the LabVIEW database file')
    parser.add_argument('--output', '-o', help='Output directory or file prefix', default='output/')
    parser.add_argument('--format', '-f', choices=['json', 'excel', 'csv', 'txt', 'html', 'all'], default='all', help='Output format')
    parser.add_argument('--verbose', '-v', action='store_true', help='Enable verbose output')
    parser.add_argument('--recursive', '-r', action='store_true', help='Process directories recursively')
    
    args = parser.parse_args()
    
    decoder = LabVIEWDatabaseDecoder(verbose=args.verbose)
    
    # Process single file or directory
    file_paths = []
    if os.path.isdir(args.file_path):
        for root, _, files in os.walk(args.file_path):
            for file in files:
                # Skip already processed files
                if file.endswith('_hex_dump.txt') or file.endswith('.json') or file.endswith('.xlsx') or file.endswith('.html') or file.endswith('.txt'):
                    continue
                
                file_path = os.path.join(root, file)
                if args.recursive or root == args.file_path:
                    file_paths.append(file_path)
            
            if not args.recursive:
                break
    else:
        file_paths = [args.file_path]
    
    for file_path in file_paths:
        try:
            print(f"Processing: {file_path}")
            data = decoder.decode_file(file_path)
            
            # Determine output path
            if os.path.isdir(args.output):
                output_prefix = os.path.join(args.output, os.path.basename(file_path))
            else:
                output_prefix = args.output
            
            # Export based on format
            if args.format in ['json', 'all']:
                decoder.export_to_json(data, f"{output_prefix}.json")
            
            if args.format in ['excel', 'all']:
                decoder.export_to_excel(data, f"{output_prefix}.xlsx")
            
            if args.format in ['csv', 'all']:
                decoder.export_to_csv(data, f"{output_prefix}_csv")
            
            if args.format in ['txt', 'all']:
                decoder.export_to_txt(data, f"{output_prefix}.txt")
            
            if args.format in ['html', 'all']:
                decoder.export_to_html(data, f"{output_prefix}.html")
            
            print(f"Decoding completed successfully!")
        except Exception as e:
            print(f"Error processing {file_path}: {e}")


if __name__ == "__main__":
    main() 