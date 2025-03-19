import streamlit as st
import pandas as pd
import requests
import json
import re
import io
import time
from datetime import datetime
import PyPDF2
import base64

# Core commands for spring testing with detailed descriptions
COMMANDS = {
    "ZF": "Tare force", 
    "ZD": "Zero Displacement", 
    "TH": "Threshold",
    "LP": "Loop", 
    "Mv(P)": "Move to Position", 
    "TD": "Time Delay", 
    "PMsg": "Print Message", 
    "Fr(P)": "Force at Position",
    "FL(P)": "Measure Free Length", 
    "Scrag": "Scragging", 
    "SR": "Spring Rate",
    "PkF": "Peak Force", 
    "PkP": "Peak Position", 
    "Po(F)": "Position at Force",
    "Po(PkF)": "Position at Peak Force", 
    "Mv(F)": "Move to Force"
}

# Standard speed values for different command types
STANDARD_SPEEDS = {
    "ZF": "50",         # Tare force - slow speed for accuracy
    "ZD": "50",         # Zero Displacement - slow speed for accuracy
    "TH": "50",         # Threshold - slow speed for precision
    "Mv(P)": "100",     # Move to Position - standard test speed
    "TD": "",           # Time Delay - no speed needed
    "PMsg": "",         # Print Message - no speed needed
    "Fr(P)": "100",     # Force at Position - standard test speed
    "FL(P)": "100",     # Free Length - standard test speed
    "Scrag": "300",     # Scragging - fast speed for cycling
    "SR": "",           # Spring Rate - no speed needed
    "LP": "",           # Loop - no speed needed
    "default": "100"    # Default standard speed
}

def call_api(parameters, api_key):
    url = "https://chat01.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Simplified system prompt focused on PDF specifications
    system_prompt = """
    Generate a spring test sequence using these exact rules:

    1. Initial Setup (first 3 rows):
       R00: ZF (Tare force) - no condition, 50 rpm
       R01: TH (Threshold) - 5N condition, 50 rpm
       R02: FL(P) (Free length) - no condition, use PDF free length for tolerance (±1mm), 100 rpm

    2. Test Points (for each set point from PDF):
       - Mv(P): Move to position from PDF (Set Point X Position), 100 rpm
       - Fr(P): Measure force, use PDF load value for tolerance (±10%), 100 rpm
       - TD: 3 second delay, no speed

    3. End Sequence (last row):
       - PMsg: Print "Test Complete"

    Rules for each column:
    - Row: Use "R00", "R01", etc.
    - CMD: Exact command from list
    - Description: Standard description
    - Condition: Exact value (5N) or blank
    - Unit: "N" for force, "mm" for position, "Sec" for time
    - Tolerance: Use format "nominal(min,max)" or blank
    - Speed rpm: Exact speed or blank for TD/PMsg

    Return JSON array with these columns exactly.
    """

    # Simplified user prompt
    user_prompt = f"""
    Using these specifications from PDF:
    Free Length: {parameters.get('Free Length')}mm
    Set Point 1: {parameters.get('Set Point 1 Position')}mm @ {parameters.get('Set Point 1 Load')}N
    Set Point 2: {parameters.get('Set Point 2 Position')}mm @ {parameters.get('Set Point 2 Load')}N
    Set Point 3: {parameters.get('Set Point 3 Position')}mm @ {parameters.get('Set Point 3 Load')}N

    Generate compression test sequence.
    """

    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.1
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        response_json = response.json()
        
        message = response_json['choices'][0].get('message', {})
        raw_content = message.get('content', '')
        
        # Extract JSON from the response
        json_match = re.search(r'```json\n(.*?)\n```|(\[.*\])', raw_content, re.DOTALL)
        if json_match:
            json_content = json_match.group(1) or json_match.group(2)
        else:
            json_content = raw_content
            
        # Clean up any remaining markdown
        json_content = re.sub(r'^```.*|```$', '', json_content, flags=re.MULTILINE).strip()
        
        # Parse JSON and convert to DataFrame
        data = json.loads(json_content)
        df = pd.DataFrame(data)
        
        # Ensure all required columns are present and in correct order
        required_columns = ["Row", "CMD", "Description", "Condition", "Unit", "Tolerance", "Speed rpm"]
        for col in required_columns:
            if col not in df.columns:
                df[col] = ""
        
        # Reorder columns
        df = df[required_columns]
        
        # Clean up empty values
        df = df.replace({"N/A": "", "None": "", "null": ""})
        
        return df
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return pd.DataFrame()

def extract_parameters(text):
    """Extract spring parameters from text with improved pattern matching for PDF specs"""
    parameters = {}
    
    # Enhanced parameter extraction patterns for PDF specifications
    patterns = {
        "Part Name": r'Part\s*Name\s*[:]*\s*([A-Za-z0-9\s\-_]+)',
        "Part Number": r'Part\s*Number\s*[:]*\s*([A-Za-z0-9\s\-_]+)',
        "ID": r'ID\s*[:]*\s*(\d+\.?\d*)',
        "Free Length": r'Free\s*Length\s*[:]*\s*(\d+\.?\d*)',
        "No of Coils": r'No\s*of\s*Colis\s*[:]*\s*(\d+\.?\d*)',
        "Wire Diameter": r'(?:Wire[d]?\s*Dia|Wired\s*Dia)\s*[:]*\s*(\d+\.?\d*)',
        "Outer Diameter": r'(?:OD|Outer\s*Diameter)\s*[:]*\s*(\d+\.?\d*)',
        "Set Point 1 Position": r'Set\s*Poni-1\s*in\s*mm\s*[:]*\s*(\d+\.?\d*)',
        "Set Point 1 Load": r'Set\s*Point-1\s*Load\s*In\s*N\s*[:]*\s*(\d+\.?\d*)(?:\s*±\s*\d+%)?',
        "Set Point 2 Position": r'Set\s*Poni-2\s*in\s*mm\s*[:]*\s*(\d+\.?\d*)',
        "Set Point 2 Load": r'Set\s*Point-2\s*Load\s*In\s*N\s*[:]*\s*(\d+\.?\d*)(?:\s*±\s*\d+%)?',
        "Set Point 3 Position": r'Set\s*Poni-3\s*in\s*mm\s*[:]*\s*(\d+\.?\d*)',
        "Set Point 3 Load": r'Set\s*Point-3\s*Load\s*In\s*N\s*[:]*\s*(\d+\.?\d*)(?:\s*±\s*\d+%)?'
    }
    
    # Extract test type (default to compression)
    parameters["Test Type"] = "Compression"
    
    # Extract parameters based on patterns
    for param, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            # Convert to float if it's a numeric value
            if param not in ["Part Name", "Part Number"]:
                try:
                    # Remove any 'mm' or 'N' suffixes before converting to float
                    value = re.sub(r'[^\d.]', '', value)
                    parameters[param] = float(value)
                except ValueError:
                    parameters[param] = value
            else:
                parameters[param] = value
    
    # Add timestamp
    parameters["Timestamp"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    return parameters

def generate_component_specs(parameters):
    """Generate component specifications dataframe from parameters"""
    specs = []
    si_no = 1
    
    # Order of specifications
    spec_order = [
        "Part Number", "Model Number", "Customer ID", "Free Length", 
        "Wire Diameter", "Outer Diameter", "Inner Diameter", 
        "Spring Rate", "Test Load", "Working Length", "Deflection"
    ]
    
    # Add parameters in the desired order
    for key in spec_order:
        if key in parameters:
            # Define unit based on parameter type
            if key in ["Free Length", "Wire Diameter", "Outer Diameter", "Inner Diameter", "Working Length", "Deflection"]:
                unit = "mm"
            elif key in ["Spring Rate"]:
                unit = "N/mm"
            elif key in ["Test Load"]:
                unit = "N"
            else:
                unit = "--"
            
            specs.append({
                "SI No": si_no,
                "Parameter": key,
                "Unit": unit,
                "Value": str(parameters[key])
            })
            si_no += 1
        
    return pd.DataFrame(specs) if specs else pd.DataFrame(columns=["SI No", "Parameter", "Unit", "Value"])

def format_chat_message(message, is_user=True):
    """Format a chat message with proper styling"""
    if is_user:
        return f"""
        <div style="display: flex; justify-content: flex-end; margin-bottom: 10px;">
            <div style="background-color: #E9F5FE; padding: 10px 15px; border-radius: 15px 15px 0 15px; max-width: 80%; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                <p style="margin: 0; color: #0A66C2; font-weight: 500;">{message}</p>
            </div>
        </div>
        """
    else:
        return f"""
        <div style="display: flex; justify-content: flex-start; margin-bottom: 10px;">
            <div style="background-color: #F0F2F5; padding: 10px 15px; border-radius: 15px 15px 15px 0; max-width: 80%; box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                <p style="margin: 0; color: #333;">{message}</p>
            </div>
        </div>
        """

def display_chat_messages():
    """Display chat messages with proper styling"""
    chat_html = ""
    
    for message in st.session_state.chat_history:
        if message["role"] == "user":
            chat_html += format_chat_message(message["content"], is_user=True)
        else:
            chat_html += format_chat_message(message["content"], is_user=False)
    
    st.markdown(chat_html, unsafe_allow_html=True)

def extract_specs_from_pdf(pdf_file):
    """Extract specifications from uploaded PDF file"""
    try:
        # Read PDF file
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        
        # Extract text from all pages
        for page in pdf_reader.pages:
            text += page.extract_text()
        
        # Extract parameters using the same patterns as natural language input
        parameters = extract_parameters(text)
        
        if parameters:
            return parameters, None
        else:
            return None, "Could not find spring specifications in the PDF."
    except Exception as e:
        return None, f"Error processing PDF: {str(e)}"

def main():
    st.set_page_config(
        page_title="Spring Test Sequence Generator",
        page_icon="🔄",
        layout="wide"
    )
    
    # Initialize session state variables
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'current_sequence' not in st.session_state:
        st.session_state.current_sequence = None
    if 'message_counter' not in st.session_state:
        st.session_state.message_counter = 0
    if 'pdf_specs' not in st.session_state:
        st.session_state.pdf_specs = None
    
    st.title("🔄 Spring Test Sequence Generator")
    
    # Sidebar for API key and command reference
    with st.sidebar:
        api_key = st.text_input("Enter API Key", type="password")
        st.markdown("### Command Reference")
        cmd_df = pd.DataFrame({
            "Command": list(COMMANDS.keys()),
            "Description": list(COMMANDS.values())
        })
        st.dataframe(cmd_df)
        
        # PDF upload section in sidebar
        st.markdown("### Upload Specifications")
        uploaded_file = st.file_uploader("Upload PDF with specifications", type=['pdf'])
        
        if uploaded_file is not None:
            specs, error = extract_specs_from_pdf(uploaded_file)
            if specs:
                st.session_state.pdf_specs = specs
                st.success("Successfully extracted specifications from PDF!")
                
                # Display extracted specifications
                st.markdown("### Extracted Specifications")
                specs_df = generate_component_specs(specs)
                st.dataframe(specs_df)
            else:
                st.error(error)
        
        if st.button("Clear Chat"):
            st.session_state.chat_history = []
            st.session_state.current_sequence = None
            st.session_state.message_counter = 0
            st.session_state.pdf_specs = None
            st.experimental_rerun()
    
    # Create two columns for chat and results
    col1, col2 = st.columns([1, 1])
    
    # Left column - Chat interface
    with col1:
        st.markdown("### Spring Test Chat Assistant")
        
        # Display chat history using expanders
        for idx, message in enumerate(st.session_state.chat_history):
            with st.expander(f"Message {idx + 1}", expanded=True):
                if message["role"] == "user":
                    st.markdown("**You:**")
                    st.markdown(f"```{message['content']}```")
                else:
                    st.markdown("**Assistant:**")
                    st.markdown(message["content"])
        
        # User input section
        with st.form("chat_form"):
            if not st.session_state.pdf_specs:
                st.warning("Please upload a PDF with spring specifications first.")
            else:
                st.success("PDF specifications loaded. Ready to generate test sequence.")
            
            user_input = st.text_input(
                "Enter command:",
                placeholder="Type: generate test sequence for compression test type"
            )
            submit_button = st.form_submit_button("Generate Sequence")
            
            if submit_button:
                if not api_key:
                    st.error("Please enter an API key in the sidebar.")
                elif not st.session_state.pdf_specs:
                    st.error("Please upload a PDF with specifications first.")
                elif "generate test sequence" in user_input.lower():
                    try:
                        with st.spinner("Generating test sequence..."):
                            # Use parameters from PDF
                            parameters = st.session_state.pdf_specs
                            
                            # Generate test sequence
                            df = call_api(parameters, api_key)
                            
                            if not df.empty:
                                st.session_state.current_sequence = df
                                response = "Test sequence generated successfully using PDF specifications."
                                
                                # Add messages to chat history
                                st.session_state.chat_history.extend([
                                    {
                                        "role": "user",
                                        "content": user_input,
                                        "id": st.session_state.message_counter
                                    },
                                    {
                                        "role": "assistant",
                                        "content": response,
                                        "id": st.session_state.message_counter + 1
                                    }
                                ])
                                st.session_state.message_counter += 2
                                st.experimental_rerun()
                            else:
                                st.error("Could not generate sequence. Please check the PDF specifications.")
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")
                else:
                    st.error('Please type "generate test sequence for compression test type"')
    
    # Right column - Results
    with col2:
        st.markdown("### Generated Test Sequence")
        
        if st.session_state.current_sequence is not None:
            # Handle empty speed values
            df = st.session_state.current_sequence.copy()
            df['Speed rpm'] = df['Speed rpm'].replace('', None)
            df['Speed rpm'] = pd.to_numeric(df['Speed rpm'], errors='coerce')
            
            # Display the DataFrame without key parameter
            st.dataframe(df)
            
            # Download options
            st.markdown("### Download Options")
            
            # Create download buttons side by side using CSS
            st.markdown(
                """
                <style>
                .download-buttons {
                    display: flex;
                    gap: 10px;
                }
                </style>
                """,
                unsafe_allow_html=True
            )
            
            # Create download buttons container
            st.markdown('<div class="download-buttons">', unsafe_allow_html=True)
            
            # CSV Download button
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="test_sequence.csv",
                mime="text/csv"
            )
            
            # JSON Download button
            json_str = df.to_json(orient="records", indent=2)
            st.download_button(
                label="Download JSON",
                data=json_str,
                file_name="test_sequence.json",
                mime="application/json"
            )
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.info("Generated test sequence will appear here.")

if __name__ == "__main__":
    main()