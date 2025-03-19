import streamlit as st
import pandas as pd
import requests
import json
import re
import io
import time
from datetime import datetime

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

    # Enhanced system prompt with more precise industry specifications
    system_prompt = """
    You are an expert AI in spring force testing systems. Generate test sequences exactly matching this format:

    COMMAND SEQUENCE:
    1. Initial Setup:
       - ZF: Tare force (leave condition blank)
       - TH: Threshold at 5N exactly
       - FL(P): Free length measurement with tolerance (e.g., 120(119,121))
       
    2. Position Setup:
       - Mv(P): Move to calculated position =(R02-24.3)
       - Mv(P): Home position (absolute value)
       
    3. Conditioning:
       - Scrag: Format "R03,2" for 2 cycles
       - TH: Search contact at 5N
       - FL(P): Verify free length
       
    4. Test Points:
       - LP: Loop start "R08,3" for 3 cycles
       - Mv(P): L1 position =(R07-14.3)
       - Fr(P): F1 measurement with tolerance
       - TD: 3 second delay
       - Mv(P): L2 position =(R07-24.3)
       - LP: Loop end
       - PMsg: Print "Test Complete"

    EXACT FORMAT RULES:
    1. Conditions:
       - Leave blank for ZF, not "N/A" or "No condition"
       - TH: Always use 5N
       - Mv(P): Use exact formulas like =(R02-24.3)
       - Scrag: Use format R03,2
       - TD: Use exact seconds (3)
       - LP: Use format R08,3 for start, blank for end
       - PMsg: Use "Test Complete" as final message
       
    2. Units:
       - Force: N
       - Position: mm
       - Time: Sec
       - Leave blank when not applicable
       
    3. Tolerances:
       - Leave blank when not applicable
       - Length: nominal(min,max) e.g., 120(119,121)
       - Force: nominal(min,max) e.g., 2799(2659,2939)
       
    4. Speeds:
       - TH: 50 rpm
       - FL(P): 100 rpm
       - Mv(P): 200 rpm for home, 100 rpm for test
       - Fr(P): 100 rpm
       - make sure to use the correct speed for each command which are accurate based on your simulation
       - Leave blank for TD, LP, PMsg, and other commands that don't need speed

    OUTPUT FORMAT:
    Return JSON array with:
    - Row: "R00", "R01", etc.
    - CMD: Exact command from list
    - Description: Match example descriptions exactly
    - Condition: Exact formula or value, leave blank where not needed
    - Unit: N, mm, or Sec only, leave blank where not needed
    - Tolerance: nominal(min,max) format, leave blank where not needed
    - Speed rpm: Match example speeds, leave blank where not needed
    """

    # Format parameter text for prompt
    parameter_text = "\n".join([f"{k}: {v}" for k, v in parameters.items() if k != "Timestamp"])
    
    # Enhanced user prompt to match example format
    user_prompt = f"""
    Generate a test sequence for a spring with these parameters:
    {parameter_text}

    Follow this exact sequence:
    1. Initial Setup:
       - ZF: Tare force (no condition)
       - TH: Threshold at 5N
       - FL(P): Free length measurement with tolerance
       
    2. Position Setup:
       - Mv(P): Move to position =(R02-24.3)
       - Mv(P): Home position 123
       
    3. Conditioning:
       - Scrag: Format R03,2
       - TH: Search contact at 5N
       - FL(P): Verify free length
       
    4. Test Points:
       - LP: Loop start R08,3
       - Mv(P): L1 position =(R07-14.3)
       - Fr(P): F1 measurement
       - TD: 3 second delay
       - Mv(P): L2 position =(R07-24.3)
       - LP: Loop end
       - PMsg: Print "Test Complete"

    Use exact speeds:
    - TH: 50 rpm
    - FL(P): 100 rpm
    - Mv(P): 200 rpm for home, 100 rpm for test
    - Fr(P): 100 rpm
    - Leave blank for TD, LP, PMsg and other commands

    Return JSON array matching the example format exactly.
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
    """Extract spring parameters from natural language text with improved pattern matching"""
    parameters = {}
    
    # Enhanced parameter extraction patterns
    patterns = {
        "Free Length": r'free\s*length\s*(?:[=:]|is|of)?\s*(\d+\.?\d*)\s*(?:mm)?',
        "Part Number": r'part\s*(?:number|#|no\.?)?\s*(?:[=:]|is)?\s*([A-Za-z0-9-_]+)',
        "Model Number": r'model\s*(?:number|#|no\.?)?\s*(?:[=:]|is)?\s*([A-Za-z0-9-_]+)',
        "Wire Diameter": r'wire\s*(?:diameter|thickness)?\s*(?:[=:]|is)?\s*(\d+\.?\d*)\s*(?:mm)?',
        "Outer Diameter": r'(?:outer|outside)\s*diameter\s*(?:[=:]|is)?\s*(\d+\.?\d*)\s*(?:mm)?',
        "Inner Diameter": r'(?:inner|inside)\s*diameter\s*(?:[=:]|is)?\s*(\d+\.?\d*)\s*(?:mm)?',
        "Spring Rate": r'(?:spring|target)\s*rate\s*(?:[=:]|is)?\s*(\d+\.?\d*)',
        "Test Load": r'(?:test|target)\s*load\s*(?:[=:]|is)?\s*(\d+\.?\d*)',
        "Deflection": r'deflection\s*(?:[=:]|is)?\s*(\d+\.?\d*)',
        "Working Length": r'working\s*length\s*(?:[=:]|is)?\s*(\d+\.?\d*)',
        "Customer ID": r'customer\s*(?:id|number)?\s*(?:[=:]|is)?\s*([A-Za-z0-9\s]+)',
    }
    
    # Extract test type
    if re.search(r'\b(?:compress|compression)\b', text, re.IGNORECASE):
        parameters["Test Type"] = "Compression"
    elif re.search(r'\b(?:tens|tension|extension|extend)\b', text, re.IGNORECASE):
        parameters["Test Type"] = "Tension"
    else:
        # Default to compression if not specified
        parameters["Test Type"] = "Compression"
    
    # Extract parameters based on patterns
    for param, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            value = match.group(1).strip()
            # Convert to float if it's a numeric value
            if param not in ["Part Number", "Model Number", "Customer ID"]:
                try:
                    parameters[param] = float(value)
                except ValueError:
                    parameters[param] = value
            else:
                parameters[param] = value
    
    # Add timestamp to parameters
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
        
        if st.button("Clear Chat"):
            st.session_state.chat_history = []
            st.session_state.current_sequence = None
            st.session_state.message_counter = 0
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
            user_input = st.text_area(
                "Enter your request:",
                height=100,
                placeholder="Example: Generate a test sequence for a compression spring with free length 120mm and part number 10KN spring"
            )
            submit_button = st.form_submit_button("Generate Sequence")
            
            if submit_button:
                if not api_key:
                    st.error("Please enter an API key in the sidebar.")
                elif user_input:
                    # Extract parameters from natural language input
                    parameters = extract_parameters(user_input)
                    
                    if not parameters or "Free Length" not in parameters:
                        st.error("Please provide at least the free length of the spring.")
                        return
                    
                    try:
                        with st.spinner("Generating test sequence..."):
                            # Generate test sequence
                            df = call_api(parameters, api_key)
                            
                            if not df.empty:
                                st.session_state.current_sequence = df
                                response = "I've generated a test sequence based on your specifications. You can see the results in the right panel."
                                
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
                                st.error("Could not generate sequence. Please check your input.")
                    except Exception as e:
                        st.error(f"An error occurred: {str(e)}")
    
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