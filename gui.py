#!/usr/bin/env python3

import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
from pathlib import Path
import shutil

# Import the encoder and decoder functions
try:
    from encoder import process_file as encode_file, create_hex_dump
    from reverser import process_file as decode_file
except ImportError:
    messagebox.showerror("Import Error", "Could not import encoder.py or reverser.py. Make sure they are in the same directory.")

class SpringFileConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Spring Force Test File Converter")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Set up the main frame
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Initialize directory variables first
        self.last_input_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DATA")
        self.last_output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "DATA", "output")
        
        # Create output directories if they don't exist
        os.makedirs(self.last_output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.last_output_dir, "encoder"), exist_ok=True)
        
        # Store recent files
        self.recent_files = []
        
        # Create notebook (tabs)
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create tabs
        self.encoder_tab = ttk.Frame(self.notebook)
        self.decoder_tab = ttk.Frame(self.notebook)
        self.viewer_tab = ttk.Frame(self.notebook)
        self.help_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.encoder_tab, text="Encoder (Binary → Text)")
        self.notebook.add(self.decoder_tab, text="Decoder (Text → Binary)")
        self.notebook.add(self.viewer_tab, text="File Viewer")
        self.notebook.add(self.help_tab, text="Help")
        
        # Set up each tab
        self.setup_encoder_tab()
        self.setup_decoder_tab()
        self.setup_viewer_tab()
        self.setup_help_tab()
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def setup_encoder_tab(self):
        # Frame for input options
        input_frame = ttk.LabelFrame(self.encoder_tab, text="Input (Binary File)", padding="10")
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # File selection
        ttk.Label(input_frame, text="Binary File:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.encoder_input_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.encoder_input_var, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(input_frame, text="Browse...", command=self.browse_encoder_input).grid(row=0, column=2, padx=5, pady=5)
        
        # Output options frame
        output_frame = ttk.LabelFrame(self.encoder_tab, text="Output Options", padding="10")
        output_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Output directory
        ttk.Label(output_frame, text="Output Directory:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.encoder_output_dir_var = tk.StringVar()
        self.encoder_output_dir_var.set(self.last_output_dir)
        ttk.Entry(output_frame, textvariable=self.encoder_output_dir_var, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(output_frame, text="Browse...", command=self.browse_encoder_output).grid(row=0, column=2, padx=5, pady=5)
        
        # Output format
        ttk.Label(output_frame, text="Output Format:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.encoder_format_var = tk.StringVar(value="all")
        format_frame = ttk.Frame(output_frame)
        format_frame.grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        ttk.Radiobutton(format_frame, text="Text", variable=self.encoder_format_var, value="txt").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(format_frame, text="JSON", variable=self.encoder_format_var, value="json").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(format_frame, text="Both", variable=self.encoder_format_var, value="all").pack(side=tk.LEFT, padx=5)
        
        # Convert button
        convert_frame = ttk.Frame(self.encoder_tab)
        convert_frame.pack(fill=tk.X, padx=5, pady=10)
        ttk.Button(convert_frame, text="Convert Binary to Text", command=self.run_encoder, style="Accent.TButton").pack(pady=10)
        
        # Results frame
        results_frame = ttk.LabelFrame(self.encoder_tab, text="Results", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Results text area
        self.encoder_results = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD, height=10)
        self.encoder_results.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.encoder_results.config(state=tk.DISABLED)
    
    def setup_decoder_tab(self):
        # Frame for input options
        input_frame = ttk.LabelFrame(self.decoder_tab, text="Input (Text File)", padding="10")
        input_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # File selection
        ttk.Label(input_frame, text="Text File:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.decoder_input_var = tk.StringVar()
        ttk.Entry(input_frame, textvariable=self.decoder_input_var, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(input_frame, text="Browse...", command=self.browse_decoder_input).grid(row=0, column=2, padx=5, pady=5)
        
        # Output options frame
        output_frame = ttk.LabelFrame(self.decoder_tab, text="Output Options", padding="10")
        output_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Output directory
        ttk.Label(output_frame, text="Output Directory:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.decoder_output_dir_var = tk.StringVar()
        self.decoder_output_dir_var.set(os.path.join(self.last_output_dir, "input"))
        ttk.Entry(output_frame, textvariable=self.decoder_output_dir_var, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(output_frame, text="Browse...", command=self.browse_decoder_output).grid(row=0, column=2, padx=5, pady=5)
        
        # Convert button
        convert_frame = ttk.Frame(self.decoder_tab)
        convert_frame.pack(fill=tk.X, padx=5, pady=10)
        ttk.Button(convert_frame, text="Convert Text to Binary", command=self.run_decoder, style="Accent.TButton").pack(pady=10)
        
        # Results frame
        results_frame = ttk.LabelFrame(self.decoder_tab, text="Results", padding="10")
        results_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Results text area
        self.decoder_results = scrolledtext.ScrolledText(results_frame, wrap=tk.WORD, height=10)
        self.decoder_results.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.decoder_results.config(state=tk.DISABLED)
    
    def setup_viewer_tab(self):
        # Top frame for file selection
        file_frame = ttk.Frame(self.viewer_tab, padding="10")
        file_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # File selection
        ttk.Label(file_frame, text="File:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.viewer_file_var = tk.StringVar()
        ttk.Entry(file_frame, textvariable=self.viewer_file_var, width=50).grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(file_frame, text="Browse...", command=self.browse_viewer_file).grid(row=0, column=2, padx=5, pady=5)
        
        # Recent files dropdown
        ttk.Label(file_frame, text="Recent:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.recent_files_var = tk.StringVar()
        self.recent_files_dropdown = ttk.Combobox(file_frame, textvariable=self.recent_files_var, width=48, state="readonly")
        self.recent_files_dropdown.grid(row=1, column=1, padx=5, pady=5)
        self.recent_files_dropdown.bind("<<ComboboxSelected>>", self.select_recent_file)
        
        # Action buttons
        action_frame = ttk.Frame(file_frame)
        action_frame.grid(row=1, column=2, padx=5, pady=5)
        ttk.Button(action_frame, text="View", command=self.view_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Open", command=self.open_file).pack(side=tk.LEFT, padx=2)
        ttk.Button(action_frame, text="Save As", command=self.save_file_as).pack(side=tk.LEFT, padx=2)
        
        # Content frame
        content_frame = ttk.LabelFrame(self.viewer_tab, text="File Content", padding="10")
        content_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Content text area
        self.file_content = scrolledtext.ScrolledText(content_frame, wrap=tk.NONE, height=20)
        self.file_content.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Horizontal scrollbar
        h_scrollbar = ttk.Scrollbar(content_frame, orient=tk.HORIZONTAL, command=self.file_content.xview)
        h_scrollbar.pack(fill=tk.X, padx=5)
        self.file_content.config(xscrollcommand=h_scrollbar.set)
        
        # File info frame
        info_frame = ttk.LabelFrame(self.viewer_tab, text="File Information", padding="10")
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # File info
        self.file_info_var = tk.StringVar()
        self.file_info_var.set("No file selected")
        ttk.Label(info_frame, textvariable=self.file_info_var).pack(fill=tk.X, padx=5, pady=5)
    
    def setup_help_tab(self):
        # Help content
        help_frame = ttk.Frame(self.help_tab, padding="10")
        help_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        help_text = scrolledtext.ScrolledText(help_frame, wrap=tk.WORD)
        help_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add help content
        help_content = """# Spring Force Test File Converter

This application provides a graphical interface for converting spring force test files between binary and text formats.

## Encoder Tab (Binary → Text)

Use this tab to convert binary spring force test files to human-readable text format.

1. Click "Browse..." to select a binary input file
2. Choose the output directory (default is DATA/output)
3. Select the output format (Text, JSON, or Both)
4. Click "Convert Binary to Text"
5. The results will be displayed in the text area

## Decoder Tab (Text → Binary)

Use this tab to convert text files back to binary format.

1. Click "Browse..." to select a text input file
2. Choose the output directory (default is DATA/output/input)
3. Click "Convert Text to Binary"
4. The results will be displayed in the text area

## File Viewer Tab

Use this tab to view and manage converted files.

1. Click "Browse..." to select a file to view
2. Or select a recently viewed file from the dropdown
3. Click "View" to display the file content
4. Click "Open" to open the file with the default application
5. Click "Save As" to save a copy of the file

## File Formats

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

- ZF: Zero Force - Reset the force sensor to zero
- ZD: Zero Displacement - Reset position measurement
- TH: Threshold (Search Contact) - Find contact with the spring
- FL(P): Measure Free Length - Measure uncompressed spring length
- Mv(P): Move to Position - Move to specific displacement
- Scrag: Scragging - Pre-load spring before testing
- Fr(P): Force at Position - Measure force at specific position
- TD: Time Delay - Add waiting period
- PMsg: User Message - Display operator messages
- LP: Loop - Create repetitive sequences
"""
        
        help_text.insert(tk.END, help_content)
        help_text.config(state=tk.DISABLED)
    
    def browse_encoder_input(self):
        file_path = filedialog.askopenfilename(
            initialdir=self.last_input_dir,
            title="Select Binary File",
            filetypes=(("All Files", "*.*"),)
        )
        if file_path:
            self.encoder_input_var.set(file_path)
            self.last_input_dir = os.path.dirname(file_path)
    
    def browse_encoder_output(self):
        dir_path = filedialog.askdirectory(
            initialdir=self.last_output_dir,
            title="Select Output Directory"
        )
        if dir_path:
            self.encoder_output_dir_var.set(dir_path)
            self.last_output_dir = dir_path
    
    def browse_decoder_input(self):
        file_path = filedialog.askopenfilename(
            initialdir=self.last_output_dir,
            title="Select Text File",
            filetypes=(("Text Files", "*.txt"), ("All Files", "*.*"))
        )
        if file_path:
            self.decoder_input_var.set(file_path)
    
    def browse_decoder_output(self):
        dir_path = filedialog.askdirectory(
            initialdir=os.path.join(self.last_output_dir, "input"),
            title="Select Output Directory"
        )
        if dir_path:
            self.decoder_output_dir_var.set(dir_path)
    
    def browse_viewer_file(self):
        file_path = filedialog.askopenfilename(
            initialdir=self.last_output_dir,
            title="Select File to View",
            filetypes=(("Text Files", "*.txt"), ("JSON Files", "*.json"), ("All Files", "*.*"))
        )
        if file_path:
            self.viewer_file_var.set(file_path)
            self.add_to_recent_files(file_path)
            self.view_file()
    
    def run_encoder(self):
        input_file = self.encoder_input_var.get()
        output_dir = self.encoder_output_dir_var.get()
        output_format = self.encoder_format_var.get()
        
        if not input_file:
            messagebox.showerror("Error", "Please select an input file")
            return
        
        if not os.path.exists(input_file):
            messagebox.showerror("Error", f"Input file does not exist: {input_file}")
            return
        
        if not output_dir:
            messagebox.showerror("Error", "Please select an output directory")
            return
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(os.path.join(output_dir, "encoder"), exist_ok=True)
        
        # Update status
        self.status_var.set(f"Converting {os.path.basename(input_file)} to text...")
        self.root.update_idletasks()
        
        try:
            # Call the encoder function
            encode_file(input_file, output_dir, output_format)
            
            # Get the output file paths
            base_name = Path(input_file).stem.replace('~', '_').replace(' ', '_')
            txt_output_path = os.path.join(output_dir, f"{base_name}.txt")
            hex_output_path = os.path.join(output_dir, "encoder", f"{base_name}_hex_dump.txt")
            json_output_path = os.path.join(output_dir, f"{base_name}.json")
            
            # Update results
            self.encoder_results.config(state=tk.NORMAL)
            self.encoder_results.delete(1.0, tk.END)
            self.encoder_results.insert(tk.END, f"Successfully converted '{input_file}':\n\n")
            
            if os.path.exists(txt_output_path):
                self.encoder_results.insert(tk.END, f"Text output: {txt_output_path}\n")
                self.add_to_recent_files(txt_output_path)
            
            if os.path.exists(hex_output_path):
                self.encoder_results.insert(tk.END, f"Hex dump: {hex_output_path}\n")
                self.add_to_recent_files(hex_output_path)
            
            if output_format in ['json', 'all'] and os.path.exists(json_output_path):
                self.encoder_results.insert(tk.END, f"JSON output: {json_output_path}\n")
                self.add_to_recent_files(json_output_path)
            
            self.encoder_results.insert(tk.END, "\nClick on the File Viewer tab to view the converted files.")
            self.encoder_results.config(state=tk.DISABLED)
            
            # Update status
            self.status_var.set("Conversion completed successfully")
            
            # Show success message
            messagebox.showinfo("Success", "File converted successfully")
            
        except Exception as e:
            # Update results with error
            self.encoder_results.config(state=tk.NORMAL)
            self.encoder_results.delete(1.0, tk.END)
            self.encoder_results.insert(tk.END, f"Error converting file: {str(e)}")
            self.encoder_results.config(state=tk.DISABLED)
            
            # Update status
            self.status_var.set("Conversion failed")
            
            # Show error message
            messagebox.showerror("Error", f"Failed to convert file: {str(e)}")
    
    def run_decoder(self):
        input_file = self.decoder_input_var.get()
        output_dir = self.decoder_output_dir_var.get()
        
        if not input_file:
            messagebox.showerror("Error", "Please select an input file")
            return
        
        if not os.path.exists(input_file):
            messagebox.showerror("Error", f"Input file does not exist: {input_file}")
            return
        
        if not output_dir:
            messagebox.showerror("Error", "Please select an output directory")
            return
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Update status
        self.status_var.set(f"Converting {os.path.basename(input_file)} to binary...")
        self.root.update_idletasks()
        
        try:
            # Call the decoder function
            decode_file(input_file, output_dir)
            
            # Get the output file paths
            base_name = Path(input_file).stem
            output_name = base_name.replace('_', ' ', 1).replace('_', '~', 1)
            binary_output_path = os.path.join(output_dir, output_name)
            hex_output_path = os.path.join(output_dir, f"{output_name}_hex_dump")
            
            # Update results
            self.decoder_results.config(state=tk.NORMAL)
            self.decoder_results.delete(1.0, tk.END)
            self.decoder_results.insert(tk.END, f"Successfully converted '{input_file}' to binary:\n\n")
            
            if os.path.exists(binary_output_path):
                self.decoder_results.insert(tk.END, f"Binary output: {binary_output_path}\n")
                self.add_to_recent_files(binary_output_path)
            
            if os.path.exists(hex_output_path):
                self.decoder_results.insert(tk.END, f"Hex dump: {hex_output_path}\n")
                self.add_to_recent_files(hex_output_path)
            
            self.decoder_results.insert(tk.END, "\nClick on the File Viewer tab to view the hex dump.")
            self.decoder_results.config(state=tk.DISABLED)
            
            # Update status
            self.status_var.set("Conversion completed successfully")
            
            # Show success message
            messagebox.showinfo("Success", "File converted successfully")
            
        except Exception as e:
            # Update results with error
            self.decoder_results.config(state=tk.NORMAL)
            self.decoder_results.delete(1.0, tk.END)
            self.decoder_results.insert(tk.END, f"Error converting file: {str(e)}")
            self.decoder_results.config(state=tk.DISABLED)
            
            # Update status
            self.status_var.set("Conversion failed")
            
            # Show error message
            messagebox.showerror("Error", f"Failed to convert file: {str(e)}")
    
    def add_to_recent_files(self, file_path):
        # Add to recent files list (max 10)
        if file_path in self.recent_files:
            self.recent_files.remove(file_path)
        self.recent_files.insert(0, file_path)
        if len(self.recent_files) > 10:
            self.recent_files = self.recent_files[:10]
        
        # Update dropdown
        self.recent_files_dropdown['values'] = [os.path.basename(f) + " - " + f for f in self.recent_files]
    
    def select_recent_file(self, event):
        selected = self.recent_files_dropdown.get()
        if selected:
            file_path = selected.split(" - ", 1)[1]
            self.viewer_file_var.set(file_path)
            self.view_file()
    
    def view_file(self):
        file_path = self.viewer_file_var.get()
        if not file_path:
            messagebox.showerror("Error", "Please select a file to view")
            return
        
        if not os.path.exists(file_path):
            messagebox.showerror("Error", f"File does not exist: {file_path}")
            return
        
        # Update file info
        file_size = os.path.getsize(file_path)
        file_type = os.path.splitext(file_path)[1]
        file_info = f"File: {os.path.basename(file_path)}\nPath: {file_path}\nSize: {file_size} bytes\nType: {file_type}"
        self.file_info_var.set(file_info)
        
        # Clear content
        self.file_content.delete(1.0, tk.END)
        
        # Read and display file content
        try:
            if file_type.lower() in ['.txt', '.json', '']:
                # Text file
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                self.file_content.insert(tk.END, content)
            else:
                # Binary file - show hex dump
                with open(file_path, 'rb') as f:
                    binary_data = f.read()
                
                # Create hex dump
                hex_dump = create_hex_dump(binary_data)
                self.file_content.insert(tk.END, hex_dump)
            
            # Add to recent files
            self.add_to_recent_files(file_path)
            
            # Update status
            self.status_var.set(f"Viewing {os.path.basename(file_path)}")
            
        except Exception as e:
            self.file_content.insert(tk.END, f"Error reading file: {str(e)}")
            self.status_var.set("Error reading file")
    
    def open_file(self):
        file_path = self.viewer_file_var.get()
        if not file_path:
            messagebox.showerror("Error", "Please select a file to open")
            return
        
        if not os.path.exists(file_path):
            messagebox.showerror("Error", f"File does not exist: {file_path}")
            return
        
        # Open file with default application
        try:
            if sys.platform == 'win32':
                os.startfile(file_path)
            elif sys.platform == 'darwin':
                subprocess.call(['open', file_path])
            else:
                subprocess.call(['xdg-open', file_path])
            
            # Update status
            self.status_var.set(f"Opened {os.path.basename(file_path)} with default application")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open file: {str(e)}")
            self.status_var.set("Error opening file")
    
    def save_file_as(self):
        file_path = self.viewer_file_var.get()
        if not file_path:
            messagebox.showerror("Error", "Please select a file to save")
            return
        
        if not os.path.exists(file_path):
            messagebox.showerror("Error", f"File does not exist: {file_path}")
            return
        
        # Get file extension
        file_ext = os.path.splitext(file_path)[1]
        
        # Ask for save location
        save_path = filedialog.asksaveasfilename(
            initialdir=os.path.dirname(file_path),
            initialfile=os.path.basename(file_path),
            defaultextension=file_ext,
            filetypes=[("All Files", "*.*")]
        )
        
        if save_path:
            try:
                # Copy file
                shutil.copy2(file_path, save_path)
                
                # Update status
                self.status_var.set(f"Saved file as {os.path.basename(save_path)}")
                
                # Show success message
                messagebox.showinfo("Success", f"File saved as {save_path}")
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {str(e)}")
                self.status_var.set("Error saving file")

def main():
    root = tk.Tk()
    
    # Configure styles
    style = ttk.Style()
    if "clam" in style.theme_names():
        style.theme_use("clam")
    
    # Create accent button style
    style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
    
    app = SpringFileConverterApp(root)
    root.mainloop()

if __name__ == "__main__":
    main() 