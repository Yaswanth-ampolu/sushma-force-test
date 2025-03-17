import streamlit as st
import pandas as pd
import requests
import json
import re

# Core commands for spring testing
COMMANDS = {
    "ZF": "Zero Force", "ZD": "Zero Displacement", "TH": "Threshold (Search Contact)",
    "LP": "Loop", "Mv(P)": "Move to Position", "Calc": "Formula Calculation",
    "TD": "Time Delay", "PMsg": "User Message", "Fr(P)": "Force at Position",
    "FL(P)": "Measure Free Length", "Scrag": "Scragging", "SR": "Spring Rate",
    "PkF": "Measure Peak Force", "PkP": "Measure Peak Position", "Po(F)": "Position at Force",
    "Po(PkF)": "Position at Peak Force", "Mv(F)": "Move to Force", "PUi": "User Input"
}

def call_api(parameters, api_key):
    url = "https://chat01.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # Enhanced system prompt with more detailed command specifications
    system_prompt = """
    You are an expert AI in spring force testing systems. Generate a complete test sequence based on user parameters.

    Use these commands precisely (each with Row ID like R00, R01, etc.):
    - ZF: Zero Force - Reset the force sensor to zero
    - ZD: Zero Displacement - Reset position measurement
    - TH: Threshold (Search Contact) - Find contact with the spring, typically with condition 10 and unit N
    - LP: Loop - Create repetitive sequences, format: start-end,repetitions
    - Mv(P): Move to Position - Move to specific displacement, with position in mm
    - Calc: Formula Calculation - Calculate values from test data
    - TD: Time Delay - Add waiting period in seconds
    - PMsg: User Message - Display operator messages
    - Fr(P): Force at Position - Measure force at specific position
    - FL(P): Measure Free Length - Measure uncompressed spring length
    - Scrag: Scragging - Pre-load spring before testing (format: start-end,repetitions)
    - SR: Spring Rate - Calculate spring constant between two positions
    - PkF: Measure Peak Force - Record maximum force
    - PkP: Measure Peak Position - Record maximum displacement
    - Po(F): Position at Force - Measure position at specific force
    - Po(PkF): Position at Peak Force - Position when peak force occurs
    - Mv(F): Move to Force - Move until reaching specific force
    - PUi: User Input - Wait for operator input

    IMPORTANT FORMATTING RULES:
    1. Use FORMULAS in the Condition field when appropriate: =(R03-10)
    2. For tolerances use format: nominal(min,max) like 50(40,60)
    3. Use percentage-based testing at 25% and 75% of displacement
    4. For compression springs, use positive displacement values
    5. For tension springs, use negative displacement values
    6. Include scragging (pre-cycling) of springs when appropriate

    Output ONLY a JSON array with objects containing: Row, CMD, Description, Condition, Unit, Tolerance
    No explanation, just the JSON array with proper calculations based on the free length and other parameters.
    """

    # Format parameter text for prompt
    parameter_text = "\n".join([f"{k}: {v}" for k, v in parameters.items()])
    
    user_prompt = f"""
    Create a precise spring test sequence with these parameters:
    {parameter_text}

    Requirements:
    1. Use formulas in the Condition field when appropriate (like =(R03-10))
    2. Format tolerances as nominal(min,max) like 50(40,60)
    3. For {parameters.get('Test Type', 'Compression')} testing, include:
    - Zero calibration commands
    - Free length measurement
    - Testing at multiple positions
    - Spring rate calculation
    - Appropriate scragging (2-3 cycles)

    Return ONLY the JSON array with the test sequence.
    """

    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2  # Slightly increased temperature for more varied responses
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        response_json = response.json()
        
        message = response_json['choices'][0].get('message', {})
        raw_content = message.get('content', '')
        
        # Extract JSON from the response, handling potential code blocks
        json_match = re.search(r'```json\n(.*?)\n```|(\[.*\])', raw_content, re.DOTALL)
        if json_match:
            json_content = json_match.group(1) or json_match.group(2)
        else:
            json_content = raw_content
            
        # Clean up any remaining markdown or text
        json_content = re.sub(r'^```.*|```$', '', json_content, flags=re.MULTILINE).strip()
        
        # Save raw response for debugging
        st.session_state.last_raw_response = raw_content
        
        # Parse JSON and convert to DataFrame
        data = json.loads(json_content)
        return pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame()
    except Exception as e:
        st.error(f"API Error: {str(e)}")
        return pd.DataFrame()

def extract_parameters(text):
    """Extract spring parameters from natural language text"""
    parameters = {}
    
    # Basic parameters
    free_length_match = re.search(r'free\s*length\s*[=:]?\s*(\d+\.?\d*)\s*mm', text, re.IGNORECASE)
    if free_length_match:
        parameters["Free Length"] = float(free_length_match.group(1))
    
    part_match = re.search(r'part\s*(?:number|#)?\s*[=:]?\s*([A-Za-z0-9-_]+)', text, re.IGNORECASE)
    if part_match:
        parameters["Part Number"] = part_match.group(1)
    
    model_match = re.search(r'model\s*(?:number|#)?\s*[=:]?\s*([A-Za-z0-9-_]+)', text, re.IGNORECASE)
    if model_match:
        parameters["Model Number"] = model_match.group(1)
    
    # Test type detection
    if re.search(r'compress|compression', text, re.IGNORECASE):
        parameters["Test Type"] = "Compression"
    elif re.search(r'tens|tension|extension|extend', text, re.IGNORECASE):
        parameters["Test Type"] = "Tension"
    
    # Technical parameters
    safety_match = re.search(r'safety\s*limit\s*[=:]?\s*(\d+\.?\d*)', text, re.IGNORECASE)
    if safety_match:
        parameters["Safety Limit"] = float(safety_match.group(1))
    
    deflection_match = re.search(r'deflection\s*[=:]?\s*(\d+\.?\d*)', text, re.IGNORECASE)
    if deflection_match:
        parameters["Deflection"] = float(deflection_match.group(1))
    
    rate_match = re.search(r'(?:spring|target)\s*rate\s*[=:]?\s*(\d+\.?\d*)', text, re.IGNORECASE)
    if rate_match:
        parameters["Spring Rate"] = float(rate_match.group(1))
    
    return parameters

def main():
    st.set_page_config(page_title="Spring Test Sequence Generator", page_icon="🔄", layout="wide")
    st.title("🔄 Spring Force Testing Sequence Generator")
    
    # Initialize session state
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'parameters' not in st.session_state:
        st.session_state.parameters = {}
    if 'last_raw_response' not in st.session_state:
        st.session_state.last_raw_response = ""
        
    # API key input
    api_key = st.sidebar.text_input("API Key", type="password")
    
    # Main tabs
    tabs = st.tabs(["Chat Interface", "Manual Parameters"])
    
    # Chat interface tab
    with tabs[0]:
        # Display chat history
        for message in st.session_state.chat_history:
            if message["role"] == "user":
                st.text_area("You:", message["content"], height=100, disabled=True)
            else:
                if isinstance(message["content"], tuple):
                    st.text_area("Assistant:", message["content"][0], height=100, disabled=True)
                    if not message["content"][1].empty:
                        st.dataframe(message["content"][1])
                        csv = message["content"][1].to_csv(index=False)
                        st.download_button("Download CSV", data=csv, file_name="test_sequence.csv", mime="text/csv")
                else:
                    st.text_area("Assistant:", message["content"], height=100, disabled=True)
        
        # User input area
        user_input = st.text_area("Describe your spring test requirements:", height=120, 
                                placeholder="Example: Generate a test sequence for a compression spring with free length 40mm, part number SP12345, and target spring rate 5 N/mm.")
        submit_button = st.button("Generate Test Sequence")
        
        # Process user input
        if submit_button and user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            
            # Extract parameters from input text
            extracted_params = extract_parameters(user_input)
            st.session_state.parameters.update(extracted_params)
            
            if api_key:
                with st.spinner("Generating test sequence..."):
                    if st.session_state.parameters:
                        df = call_api(st.session_state.parameters, api_key)
                        if not df.empty:
                            assistant_response = ("Here's the test sequence based on your requirements:", df)
                        else:
                            assistant_response = "I couldn't generate a valid test sequence. Please provide more specific spring details."
                    else:
                        assistant_response = "Please provide specific spring details like free length, test type, etc."
                
                st.session_state.chat_history.append({"role": "assistant", "content": assistant_response})
                st.experimental_rerun()
            else:
                st.error("Please provide an API key in the sidebar.")
    
    # Manual parameter input tab
    with tabs[1]:
        col1, col2 = st.columns(2)
        with col1:
            part_number = st.text_input("Part Number", value=st.session_state.parameters.get("Part Number", "SP-001"))
            free_length = st.number_input("Free Length (mm)", min_value=0.0, value=st.session_state.parameters.get("Free Length", 50.0), step=0.5)
            deflection = st.number_input("Deflection (mm)", min_value=0.0, value=st.session_state.parameters.get("Deflection", 20.0), step=0.5)
        with col2:
            model_number = st.text_input("Model Number", value=st.session_state.parameters.get("Model Number", "M001"))
            test_type = st.selectbox("Test Type", ["Compression", "Tension"], index=0 if st.session_state.parameters.get("Test Type", "Compression") == "Compression" else 1)
            spring_rate = st.number_input("Target Spring Rate (N/mm)", min_value=0.0, value=st.session_state.parameters.get("Spring Rate", 5.0), step=0.1)
        
        safety_limit = st.slider("Safety Limit (N)", min_value=0.0, max_value=500.0, value=st.session_state.parameters.get("Safety Limit", 200.0), step=10.0)
        
        # Update parameters button
        if st.button("Update Parameters"):
            st.session_state.parameters = {
                "Part Number": part_number,
                "Model Number": model_number,
                "Free Length": free_length,
                "Test Type": test_type,
                "Safety Limit": safety_limit,
                "Deflection": deflection,
                "Spring Rate": spring_rate
            }
            st.success("Parameters updated!")
        
        # Show current parameters
        st.subheader("Current Parameters")
        st.json(st.session_state.parameters)
        
        # Generate sequence button
        if st.button("Generate Sequence from Parameters"):
            if not api_key:
                st.error("Please provide an API key")
            elif not st.session_state.parameters:
                st.error("Please update parameters first")
            else:
                with st.spinner("Generating test sequence..."):
                    df = call_api(st.session_state.parameters, api_key)
                    if not df.empty:
                        st.success("Test sequence generated successfully!")
                        st.dataframe(df)
                        csv = df.to_csv(index=False)
                        st.download_button("Download CSV", data=csv, file_name="test_sequence.csv", mime="text/csv")
                    else:
                        st.error("Failed to generate test sequence")
        
        # Display raw API response for debugging (collapsible)
        with st.expander("Debug - Raw API Response", expanded=False):
            st.text_area("Raw Response", st.session_state.last_raw_response, height=300)

if __name__ == "__main__":
    main()