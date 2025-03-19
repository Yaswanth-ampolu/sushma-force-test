#!/usr/bin/env python3

import struct
import argparse
import os
from pathlib import Path

class BinaryFormatWriter:
    """
    Class to write binary files in the National Instruments format for spring testing equipment.
    """
    def __init__(self):
        self.data = bytearray()
        
    def write_header(self):
        """Write the initial header bytes"""
        # Based on the sample, this seems to be a fixed header value
        self.data.extend(b'\x00\x00\x00\x01')
        
    def write_string(self, string):
        """
        Write a string with a 4-byte length prefix
        
        Args:
            string (str): The string to write
        """
        # Convert the string to bytes
        string_bytes = string.encode('utf-8')
        # Write the length as a 4-byte big-endian integer
        self.data.extend(struct.pack('>I', len(string_bytes)))
        # Write the string bytes
        self.data.extend(string_bytes)
        
    def write_metadata(self, part_number, model_number, free_length):
        """
        Write the metadata section
        
        Args:
            part_number (str): Part number value
            model_number (str): Model number value
            free_length (str): Free length value in mm
        """
        # Part Number
        self.write_string("Part Number")
        self.write_string("--")
        self.write_string(part_number)
        
        # Model Number
        self.write_string("Model Number")
        self.write_string("--")
        self.write_string(model_number)
        
        # Free Length
        self.write_string("Free Length")
        self.write_string("mm")
        self.write_string(free_length)
        
    def write_test_sequence_header(self, force_unit="lbf", height="125", height_val="80"):
        """
        Write the test sequence header
        
        Args:
            force_unit (str): Force unit (lbf or N or kgf)
            height (str): Height value
            height_val (str): Height value to display
        """
        self.write_string("<Test Sequence>")
        self.write_string(force_unit)  # Force unit
        self.write_string("SPRING TEST")
        self.write_string("Height")
        self.write_string(height)
        self.write_string(height_val)
        
    def write_zero_force(self):
        """Write a Zero Force command"""
        self.write_string("ZF")
        self.write_string("Zero Force")
        
    def write_search_contact(self, force, unit="lbf", value="100"):
        """
        Write a Search Contact command
        
        Args:
            force (str): Force threshold
            unit (str): Force unit
            value (str): Speed value
        """
        self.write_string("TH")
        self.write_string("Search Contact")
        self.write_string(force)
        self.write_string(unit)
        self.write_string(value)
        
    def write_measure_free_length(self, position, limits):
        """
        Write a Measure Free Length command
        
        Args:
            position (str): Position descriptor
            limits (str): Limit range in format "value(min,max)"
        """
        self.write_string("FL(P)")
        self.write_string("Measure Free Length")
        self.write_string("-Position")
        self.write_string("mm")
        self.write_string(limits)
        
    def write_move_to_position(self, position, unit="mm", speed="100"):
        """
        Write a Move to Position command
        
        Args:
            position (str): Position value
            unit (str): Position unit
            speed (str): Target speed/rate
        """
        self.write_string("Mv(P)")
        self.write_string("Move to Position")
        self.write_string(position)
        self.write_string(unit)
        self.write_string(speed)
        
    def write_force_at_position(self, unit="lbf", limits="100(80,120)"):
        """
        Write a Force at Position command
        
        Args:
            unit (str): Force unit
            limits (str): Force limits in format "value(min,max)"
        """
        self.write_string("Fr(P)")
        self.write_string("Force @ Position")
        self.write_string(unit)
        self.write_string(limits)
        
    def write_time_delay(self, time, unit="Sec"):
        """
        Write a Time Delay command
        
        Args:
            time (str): Time value
            unit (str): Time unit
        """
        self.write_string("TD")
        self.write_string("Time Delay")
        self.write_string(time)
        self.write_string(unit)
        
    def write_loop(self, loop_param="3"):
        """
        Write a Loop command
        
        Args:
            loop_param (str): Loop parameters
        """
        self.write_string("LP")
        self.write_string("Loop")
        self.write_string(loop_param)
        
    def write_home(self, position="123", speed="200"):
        """
        Write a HOME command
        
        Args:
            position (str): Home position
            speed (str): Speed value
        """
        self.write_string("Mv(P)")
        self.write_string("HOME")
        self.write_string(position)
        self.write_string("mm")
        self.write_string(speed)
        
    def write_user_message(self, message="FINISH"):
        """
        Write a User Message command
        
        Args:
            message (str): Message text
        """
        self.write_string("PMsg")
        self.write_string("User Message")
        self.write_string(message)
        
    def save_to_file(self, file_path):
        """
        Save the binary data to a file
        
        Args:
            file_path (str): Path to save the file
        """
        with open(file_path, 'wb') as f:
            f.write(self.data)
        print(f"File saved: {file_path}")


def parse_spring_test_file(text_content):
    """
    Parse a spring test text content into structured data
    
    Args:
        text_content (str): The raw text content
        
    Returns:
        dict: Structured data including metadata and test sequence
    """
    lines = text_content.strip().split('\n')
    data = {
        'metadata': {},
        'test_sequence': []
    }
    
    # Extract metadata and test sequence
    test_sequence_started = False
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if test_sequence_started:
            # Add to test sequence
            data['test_sequence'].append(line)
        elif line.startswith("<Test Sequence>"):
            test_sequence_started = True
            continue
        else:
            # Parse metadata lines like "Part Number--C-SPRING"
            parts = line.strip().split('--')
            if len(parts) == 2:
                key, value = parts[0].strip(), parts[1].strip()
                # Remove numeric prefixes like "1" from "1Part Number"
                while key and key[0].isdigit():
                    key = key[1:]
                data['metadata'][key] = value
            
            # Special case for handling free length with unit
            if line.startswith("Free Length"):
                parts = line.split('mm')
                if len(parts) == 2:
                    data['metadata']['Free Length'] = parts[0].replace("Free Length", "").strip()
                    data['metadata']['Free Length Unit'] = 'mm'
    
    return data


def create_binary_from_text_content(text_content, output_file):
    """
    Create a binary file from text content
    
    Args:
        text_content (str): The raw text content
        output_file (str): Path to save the binary file
    """
    # Parse the text content
    data = parse_spring_test_file(text_content)
    
    # Create binary writer
    writer = BinaryFormatWriter()
    writer.write_header()
    
    # Write metadata
    part_number = data['metadata'].get('Part Number', 'C-SPRING')
    model_number = data['metadata'].get('Model Number', '2022')
    free_length = data['metadata'].get('Free Length', '120')
    
    writer.write_metadata(part_number, model_number, free_length)
    
    # Parse and write the test sequence
    writer.write_test_sequence_header("lbf", "125", "80")
    
    # Process commands from test sequence
    in_command = False
    command_type = None
    
    # Direct command processing when we have raw commands from the file
    for line in data['test_sequence']:
        parts = line.split()
        if not parts:
            continue
        
        command = parts[0]
        
        if command == "ZF":
            writer.write_zero_force()
        elif command == "TH":
            # Format: "TH" "Search Contact" "1.12" "lbf" "100"
            if len(parts) >= 5:
                writer.write_search_contact(parts[2], parts[3], parts[4])
            else:
                writer.write_search_contact("1.12")
        elif command == "FL(P)":
            # Format: "FL(P)" "Measure Free Length-Position" "mm" "120(119,121)"
            if len(parts) >= 4:
                writer.write_measure_free_length("-Position", parts[3])
            else:
                writer.write_measure_free_length("-Position", "120(119,121)")
        elif command == "Mv(P)":
            # Format: "Mv(P)" "Move to Position" "105.7" "mm" "100"
            if len(parts) >= 5:
                writer.write_move_to_position(parts[2], parts[3], parts[4])
            elif len(parts) >= 3 and parts[1] == "HOME":
                writer.write_home(parts[2], parts[4] if len(parts) > 4 else "200")
            else:
                writer.write_move_to_position("105.7")
        elif command == "Fr(P)":
            # Format: "Fr(P)" "Force @ Position" "lbf" "629(580,680)"
            if len(parts) >= 4:
                writer.write_force_at_position(parts[2], parts[3])
            else:
                writer.write_force_at_position()
        elif command == "TD":
            # Format: "TD" "Time Delay" "3" "Sec"
            if len(parts) >= 4:
                writer.write_time_delay(parts[2], parts[3])
            else:
                writer.write_time_delay("3")
        elif command == "LP":
            # Format: "LP" "Loop" "3"
            if len(parts) >= 3:
                writer.write_loop(parts[2])
            else:
                writer.write_loop()
        elif command == "PMsg":
            # Format: "PMsg" "User Message" "FINISH"
            if len(parts) >= 3:
                writer.write_user_message(parts[2])
            else:
                writer.write_user_message()
    
    # Ensure the filename starts with the correct prefix
    if not os.path.basename(output_file).startswith("AS 02~"):
        output_dir = os.path.dirname(output_file)
        filename = os.path.basename(output_file)
        new_filename = f"AS 02~{part_number}"
        output_file = os.path.join(output_dir, new_filename)
    
    # Save the binary file
    writer.save_to_file(output_file)


def create_binary_from_file(input_file, output_file=None):
    """
    Create a binary file from a text file
    
    Args:
        input_file (str): Path to the text file
        output_file (str): Path to save the binary file (optional)
    """
    with open(input_file, 'r', encoding='utf-8') as f:
        text_content = f.read()
    
    # If output_file is not provided, create one based on the input file
    if not output_file:
        input_path = Path(input_file)
        output_dir = input_path.parent
        part_name = "C-SPRING"  # Default part name
        
        # Try to extract part number from content
        for line in text_content.split('\n'):
            if "Part Number" in line:
                parts = line.split(':', 1)
                if len(parts) > 1:
                    part_name = parts[1].strip()
                break
        
        output_file = output_dir / f"AS 02~{part_name}"
    
    create_binary_from_text_content(text_content, output_file)


def create_c_spring_example(output_file=None):
    """
    Create an example C-SPRING binary file based on the provided sample
    
    Args:
        output_file (str): Path to save the binary file (optional)
    """
    if not output_file:
        output_file = "AS 02~C-SPRING"
    
    # Create sample content from the first document
    sample_content = """Part Number--C-SPRING
Model Number--2022
Free Lengthmm120
<Test Sequence>
lbfSPRING TESTHeight12580
ZF
Zero Force
TH
Search Contact
1.12
lbf
100
FL(P)
Measure Free Length-Position
mm
120(119,121)
Mv(P)
Move to Position
105.7
mm
100
Fr(P)
Force @ Position
lbf
629(580,680)
TD
Time Delay
3
Sec
Mv(P)
HOME
123
mm
200
LP
Loop
R03,3
PMsg
User Message
FINISH"""
    
    create_binary_from_text_content(sample_content, output_file)


def main():
    parser = argparse.ArgumentParser(description='Create spring test binary files for National Instruments')
    parser.add_argument('--input', help='Path to the text file to convert')
    parser.add_argument('--output', help='Path to save the binary file')
    parser.add_argument('--create-example', action='store_true', help='Create an example C-SPRING binary file')
    
    args = parser.parse_args()
    
    if args.input:
        create_binary_from_file(args.input, args.output)
    elif args.create_example:
        create_c_spring_example(args.output)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()