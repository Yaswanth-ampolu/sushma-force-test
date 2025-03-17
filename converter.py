import re
import pandas as pd
import os
import json

class SpringFileDecoder:
    """
    Decoder for spring test files with no extension
    Handles both component specifications and test sequence data
    """
    
    def __init__(self):
        # Command dictionary for translation
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
        
    def parse_file(self, file_path):
        """
        Parse the spring test file and extract data
        """
        try:
            with open(file_path, 'r') as f:
                content = f.read()
        except UnicodeDecodeError:
            # Try reading as binary and decode
            with open(file_path, 'rb') as f:
                content = f.read().decode('utf-8', errors='replace')
        
        # Extract data
        data = {}
        
        # Parse component specifications
        specs = self._parse_specs(content)
        data['component_specifications'] = specs
        
        # Parse test sequence
        test_sequence = self._parse_test_sequence(content)
        data['test_sequence'] = test_sequence
        
        return data
    
    def _parse_specs(self, content):
        """
        Parse component specification data
        """
        specs = {}
        
        # Look for patterns like "1Part Number--10KN spring"
        part_pattern = r'(\d+)([A-Za-z\s]+)--([^0-9\n]+)'
        part_matches = re.findall(part_pattern, content)
        
        # Look for patterns like "2Model Number--2022"
        model_pattern = r'(\d+)([A-Za-z\s]+)--(\d+)'
        model_matches = re.findall(model_pattern, content)
        
        # Look for patterns like "3Free Lengthmm120"
        length_pattern = r'(\d+)([A-Za-z\s]+)([a-z]+)(\d+)'
        length_matches = re.findall(length_pattern, content)
        
        # Process matches
        for match in part_matches:
            si_no = match[0]
            param = match[1].strip()
            value = match[2].strip()
            specs[param] = {'SI No': si_no, 'Value': value, 'Unit': '--'}
            
        for match in model_matches:
            si_no = match[0]
            param = match[1].strip()
            value = match[2].strip()
            specs[param] = {'SI No': si_no, 'Value': value, 'Unit': '--'}
            
        for match in length_matches:
            si_no = match[0]
            param = match[1].strip()
            unit = match[2].strip()
            value = match[3].strip()
            specs[param] = {'SI No': si_no, 'Value': value, 'Unit': unit}
        
        # Look for safety limit
        safety_pattern = r'Height(\d+)'
        safety_match = re.search(safety_pattern, content)
        if safety_match:
            specs['Safety Limit'] = {'SI No': '', 'Value': safety_match.group(1), 'Unit': 'N'}
        
        return specs
    
    def _parse_test_sequence(self, content):
        """
        Parse test sequence data
        """
        # Find the test sequence section
        test_seq_start = content.find('<Test Sequence>')
        if test_seq_start == -1:
            test_seq_start = content.find('Test Sequence')
        
        if test_seq_start == -1:
            return []
        
        test_content = content[test_seq_start:]
        
        # Create a list to hold test sequence steps
        sequence = []
        
        # Common patterns in test sequence
        command_pattern = r'([A-Za-z\(\)]+)\s*([A-Za-z0-9\s\(\)\-\.]+)([A-Za-z]+)?\s*([0-9\(\)\,\.]+)'
        
        # Get individual lines from test content
        lines = test_content.split('\n')
        
        # Process the test sequence commands
        row_counter = 0
        
        # Need to handle the format where commands might be in a single line
        if len(lines) <= 3:  # If test sequence is not clearly separated by lines
            # Split by common delimiters
            commands = re.split(r'(?=[A-Z][a-z]\()', test_content)
            
            for cmd_str in commands:
                if any(cmd in cmd_str for cmd in self.command_dict.keys()):
                    # Extract command parts
                    cmd_parts = re.findall(r'([A-Za-z\(\)]+)([^A-Z]+)', cmd_str)
                    
                    for cmd, rest in cmd_parts:
                        if cmd in self.command_dict:
                            # Extract description, condition, unit, and tolerance
                            rest = rest.strip()
                            parts = re.split(r'([0-9\(\)\,\.]+)([A-Za-z]+)', rest)
                            
                            step = {
                                'Row': f'R{row_counter:02d}',
                                'CMD': cmd,
                                'Description': self.command_dict.get(cmd, cmd),
                                'Condition': '',
                                'Unit': '',
                                'Tolerance': '',
                                'Speed': ''
                            }
                            
                            if len(parts) >= 3:
                                step['Condition'] = parts[1]
                                step['Unit'] = parts[2]
                                
                                if len(parts) > 3 and parts[3]:
                                    step['Tolerance'] = parts[3]
                            
                            sequence.append(step)
                            row_counter += 1
        else:
            # Process line by line
            for line in lines:
                # Skip lines that don't contain command data
                if not any(cmd in line for cmd in self.command_dict.keys()) and not re.search(r'[A-Z][a-z]\(', line):
                    continue
                
                # Split by recognized commands
                parts = re.split(r'([A-Z][a-z]\([A-Z]\))', line)
                
                for i, part in enumerate(parts):
                    if part in self.command_dict or re.match(r'[A-Z][a-z]\([A-Z]\)', part):
                        cmd = part
                        
                        # Try to extract the next parts as parameters
                        if i+1 < len(parts):
                            params = parts[i+1]
                            
                            # Extract numbers and units
                            num_match = re.search(r'([0-9\(\)\,\.]+)', params)
                            unit_match = re.search(r'([A-Za-z]+)', params)
                            
                            condition = num_match.group(1) if num_match else ''
                            unit = unit_match.group(1) if unit_match else ''
                            
                            step = {
                                'Row': f'R{row_counter:02d}',
                                'CMD': cmd,
                                'Description': self.command_dict.get(cmd, cmd),
                                'Condition': condition,
                                'Unit': unit,
                                'Tolerance': '',
                                'Speed': ''
                            }
                            
                            sequence.append(step)
                            row_counter += 1
        
        # If the previous approach didn't work, try another pattern matching approach
        if not sequence:
            # Look for specific command patterns in the content
            zf_match = re.search(r'ZF', test_content)
            if zf_match:
                sequence.append({
                    'Row': 'R00',
                    'CMD': 'ZF',
                    'Description': 'Tare force',
                    'Condition': '',
                    'Unit': '',
                    'Tolerance': '',
                    'Speed': ''
                })
            
            th_match = re.search(r'TH\s*([A-Za-z\s]+)\s*(\d+)', test_content)
            if th_match:
                sequence.append({
                    'Row': 'R01',
                    'CMD': 'TH',
                    'Description': 'Threshold',
                    'Condition': th_match.group(2),
                    'Unit': 'N',
                    'Tolerance': '',
                    'Speed': ''
                })
            
            # Add more specific pattern matching for other commands
            # ...
        
        # If still no sequence found, use direct pattern extraction
        if not sequence:
            # Direct extraction from content
            step_pattern = r'(ZF|TH|FL\(P\)|Mv\(P\)|Scrag|Fr\(P\)|TD|PMsg|Home position)\s*([^N]+)?\s*([A-Za-z]+)?\s*(\d+(?:\(\d+,\d+\))?)?'
            steps = re.findall(step_pattern, test_content)
            
            row_counter = 0
            for cmd, desc, unit, value in steps:
                step = {
                    'Row': f'R{row_counter:02d}',
                    'CMD': cmd,
                    'Description': desc.strip() if desc else self.command_dict.get(cmd, cmd),
                    'Condition': '',
                    'Unit': unit if unit else '',
                    'Tolerance': value if value else '',
                    'Speed': ''
                }
                
                sequence.append(step)
                row_counter += 1
        
        return sequence
    
    def export_to_json(self, data, output_path):
        """
        Export parsed data to JSON format
        """
        with open(output_path, 'w') as f:
            json.dump(data, f, indent=4)
        print(f"JSON file exported to {output_path}")
    
    def export_to_excel(self, data, output_path):
        """
        Export parsed data to Excel format
        """
        # Create Excel writer
        with pd.ExcelWriter(output_path) as writer:
            # Component Specifications sheet
            specs_df = pd.DataFrame([
                {
                    'SI No': v.get('SI No', ''),
                    'Parameter': k,
                    'Unit': v.get('Unit', ''),
                    'Value': v.get('Value', '')
                }
                for k, v in data['component_specifications'].items()
            ])
            specs_df.to_excel(writer, sheet_name='Component Specifications', index=False)
            
            # Test Sequence sheet
            if data['test_sequence']:
                sequence_df = pd.DataFrame(data['test_sequence'])
                sequence_df.to_excel(writer, sheet_name='Test Sequence', index=False)
        
        print(f"Excel file exported to {output_path}")
    
    def export_to_csv(self, data, output_folder):
        """
        Export parsed data to CSV format
        """
        # Ensure output folder exists
        os.makedirs(output_folder, exist_ok=True)
        
        # Component Specifications CSV
        specs_df = pd.DataFrame([
            {
                'SI No': v.get('SI No', ''),
                'Parameter': k,
                'Unit': v.get('Unit', ''),
                'Value': v.get('Value', '')
            }
            for k, v in data['component_specifications'].items()
        ])
        specs_path = os.path.join(output_folder, "component_specifications.csv")
        specs_df.to_csv(specs_path, index=False)
        
        # Test Sequence CSV
        if data['test_sequence']:
            sequence_df = pd.DataFrame(data['test_sequence'])
            sequence_path = os.path.join(output_folder, "test_sequence.csv")
            sequence_df.to_csv(sequence_path, index=False)
        
        print(f"CSV files exported to {output_folder}")
    
    def export_to_txt(self, data, output_path):
        """
        Export parsed data to readable text format
        """
        with open(output_path, 'w') as f:
            f.write("=== SPRING TEST FILE DECODED DATA ===\n\n")
            
            # Component Specifications
            f.write("=== COMPONENT SPECIFICATIONS ===\n")
            f.write(f"{'SI No':<10}{'Parameter':<30}{'Unit':<10}{'Value':<20}\n")
            f.write("-" * 70 + "\n")
            
            for param, details in data['component_specifications'].items():
                f.write(f"{details.get('SI No', ''):<10}{param:<30}{details.get('Unit', ''):<10}{details.get('Value', ''):<20}\n")
            
            f.write("\n\n")
            
            # Test Sequence
            f.write("=== TEST SEQUENCE ===\n")
            if data['test_sequence']:
                f.write(f"{'Row':<10}{'CMD':<10}{'Description':<30}{'Condition':<20}{'Unit':<10}{'Tolerance':<20}{'Speed':<10}\n")
                f.write("-" * 100 + "\n")
                
                for step in data['test_sequence']:
                    f.write(f"{step.get('Row', ''):<10}{step.get('CMD', ''):<10}{step.get('Description', ''):<30}")
                    f.write(f"{step.get('Condition', ''):<20}{step.get('Unit', ''):<10}{step.get('Tolerance', ''):<20}")
                    f.write(f"{step.get('Speed', ''):<10}\n")
            else:
                f.write("No test sequence data found.\n")
        
        print(f"Text file exported to {output_path}")
    
    def export_to_html(self, data, output_path):
        """
        Export parsed data to HTML format
        """
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Spring Test File Decoded Data</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                h1, h2 { color: #333; }
                table { border-collapse: collapse; width: 100%; margin-bottom: 30px; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                tr:nth-child(even) { background-color: #f9f9f9; }
                .section { margin-bottom: 30px; }
            </style>
        </head>
        <body>
            <h1>Spring Test File Decoded Data</h1>
            
            <div class="section">
                <h2>Component Specifications</h2>
                <table>
                    <tr>
                        <th>SI No</th>
                        <th>Parameter</th>
                        <th>Unit</th>
                        <th>Value</th>
                    </tr>
        """
        
        # Add component specifications
        for param, details in data['component_specifications'].items():
            html_content += f"""
                    <tr>
                        <td>{details.get('SI No', '')}</td>
                        <td>{param}</td>
                        <td>{details.get('Unit', '')}</td>
                        <td>{details.get('Value', '')}</td>
                    </tr>
            """
        
        html_content += """
                </table>
            </div>
            
            <div class="section">
                <h2>Test Sequence</h2>
                <table>
                    <tr>
                        <th>Row</th>
                        <th>CMD</th>
                        <th>Description</th>
                        <th>Condition</th>
                        <th>Unit</th>
                        <th>Tolerance</th>
                        <th>Speed</th>
                    </tr>
        """
        
        # Add test sequence
        if data['test_sequence']:
            for step in data['test_sequence']:
                html_content += f"""
                    <tr>
                        <td>{step.get('Row', '')}</td>
                        <td>{step.get('CMD', '')}</td>
                        <td>{step.get('Description', '')}</td>
                        <td>{step.get('Condition', '')}</td>
                        <td>{step.get('Unit', '')}</td>
                        <td>{step.get('Tolerance', '')}</td>
                        <td>{step.get('Speed', '')}</td>
                    </tr>
                """
        else:
            html_content += """
                    <tr>
                        <td colspan="7">No test sequence data found.</td>
                    </tr>
            """
        
        html_content += """
                </table>
            </div>
        </body>
        </html>
        """
        
        with open(output_path, 'w') as f:
            f.write(html_content)
        
        print(f"HTML file exported to {output_path}")


def main():
    """
    Main function to run the decoder
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Spring Test File Decoder')
    parser.add_argument('file_path', help='Path to the spring test file')
    parser.add_argument('--output', '-o', default='output', help='Output directory or file prefix')
    parser.add_argument('--format', '-f', choices=['json', 'excel', 'csv', 'txt', 'html', 'all'], 
                        default='all', help='Output format')
    
    args = parser.parse_args()
    
    # Create decoder instance
    decoder = SpringFileDecoder()
    
    # Parse the file
    print(f"Parsing file: {args.file_path}")
    data = decoder.parse_file(args.file_path)
    
    # Create output directory if needed
    os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else '.', exist_ok=True)
    
    # Export data based on selected format
    if args.format in ['json', 'all']:
        decoder.export_to_json(data, f"{args.output}.json")
    
    if args.format in ['excel', 'all']:
        decoder.export_to_excel(data, f"{args.output}.xlsx")
    
    if args.format in ['csv', 'all']:
        decoder.export_to_csv(data, f"{args.output}_csv")
    
    if args.format in ['txt', 'all']:
        decoder.export_to_txt(data, f"{args.output}.txt")
    
    if args.format in ['html', 'all']:
        decoder.export_to_html(data, f"{args.output}.html")
    
    print("Decoding completed successfully!")


if __name__ == "__main__":
    main()