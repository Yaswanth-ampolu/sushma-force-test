import streamlit as st
import pandas as pd
import requests
import json
import re

COMMANDS = {
    "ZF": "Zero Force", "ZD": "Zero Displacement", "TH": "Threshold (Search Contact)",
    "LP": "Loop", "Mv(P)": "Move to Position", "Calc": "Formula Calculation",
    "TD": "Time Delay", "PMsg": "User Message", "Fr(P)": "Force at Position",
    "FL(P)": "Measure Free Length", "Scrag": "Scragging", "SR": "Spring Rate",
    "PkF": "Measure Peak Force", "PkP": "Measure Peak Position", "Po(F)": "Position at Force",
    "Po(PkF)": "Position at Peak Force", "Mv(F)": "Move to Force", "PUi": "User Input"
}

def call_custom_api(instruction, parameters, api_key):
    url = "https://chat01.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

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
    
    Output ONLY a JSON array with objects containing: Row, CMD, Description, Condition, Unit, Tolerance
    No explanation, just the JSON array with proper calculations based on the free length and other parameters.
    """

    parameter_text = "\n".join([f"{k}: {v}" for k, v in parameters.items()])
    user_prompt = f"""
    Create a spring test sequence with these parameters:
    {parameter_text}
    
    Return only the JSON array with fields: Row, CMD, Description, Condition, Unit, Tolerance.
    """

    payload = {
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        response_json = response.json()
        
        message = response_json['choices'][0].get('message', {})
        raw_content = message.get('content', '')
        cleaned_content = re.sub(r'^```json|```$', '', raw_content, flags=re.MULTILINE).strip()
        
        st.session_state.last_raw_response = raw_content
        data = json.loads(cleaned_content)
        
        return pd.DataFrame(data) if isinstance(data, list) else pd.DataFrame()
    except Exception as e:
        st.error(f"Error: {str(e)}")
        return pd.DataFrame()

def extract_parameters_from_text(text):
    parameters = {}
    
    free_length_match = re.search(r'free\s*length\s*[=:]?\s*(\d+\.?\d*)\s*mm', text, re.IGNORECASE)
    if free_length_match:
        parameters["Free Length"] = float(free_length_match.group(1))
    
    part_match = re.search(r'part\s*number\s*[=:]?\s*(\w+)', text, re.IGNORECASE)
    if part_match:
        parameters["Part Number"] = part_match.group(1)
    
    if re.search(r'compress|compression', text, re.IGNORECASE):
        parameters["Test Type"] = "Compression"
    elif re.search(r'tension|tensile', text, re.IGNORECASE):
        parameters["Test Type"] = "Tension"
    
    safety_match = re.search(r'safety\s*limit\s*[=:]?\s*(\d+\.?\d*)', text, re.IGNORECASE)
    if safety_match:
        parameters["Safety Limit"] = float(safety_match.group(1))
    
    deflection_match = re.search(r'deflection\s*[=:]?\s*(\d+\.?\d*)', text, re.IGNORECASE)
    if deflection_match:
        parameters["Deflection"] = float(deflection_match.group(1))
    
    return parameters

def main():
    st.set_page_config(page_title="Spring Test Sequence Generator", page_icon="🔄", layout="wide")
    st.title("🔄 AI Spring Test Sequence Generator")
    
    if 'chat_history' not in st.session_state:
        st.session_state.chat_history = []
    if 'parameters' not in st.session_state:
        st.session_state.parameters = {}
        
    api_key = st.sidebar.text_input("API Key", type="password")
    
    tab1, tab2 = st.tabs(["Chat", "Parameters"])
    
    with tab1:
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
        
        user_input = st.text_area("Describe your spring test requirements:", height=100)
        submit_button = st.button("Submit")
        
        if submit_button and user_input:
            st.session_state.chat_history.append({"role": "user", "content": user_input})
            
            extracted_params = extract_parameters_from_text(user_input)
            st.session_state.parameters.update(extracted_params)
            
            if api_key:
                with st.spinner("Generating test sequence..."):
                    if st.session_state.parameters:
                        df = call_custom_api(user_input, st.session_state.parameters, api_key)
                        assistant_response = ("Here's the test sequence based on your requirements:", df) if not df.empty else "I need more information about your spring."
                    else:
                        assistant_response = "Please provide spring details like free length, test type, etc."
                
                st.session_state.chat_history.append({"role": "assistant", "content": assistant_response})
                st.experimental_rerun()
            else:
                st.error("Please provide an API key in the sidebar.")
    
    with tab2:
        with st.expander("Manual Parameter Input", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                free_length = st.number_input("Free Length (mm)", min_value=0.0, value=50.0, step=0.5)
                part_number = st.text_input("Part Number", value="SPRING-001")
            with col2:
                test_type = st.selectbox("Test Type", ["Compression", "Tension"])
                safety_limit = st.number_input("Safety Limit (N)", min_value=0.0, value=200.0, step=10.0)
            
            col1, col2 = st.columns(2)
            with col1:
                deflection = st.number_input("Deflection (mm)", min_value=0.0, value=20.0, step=1.0)
            with col2:
                spring_rate = st.number_input("Target Spring Rate (N/mm)", min_value=0.0, value=5.0, step=0.1)
            
            parameters = {
                "Free Length": free_length, "Part Number": part_number, "Test Type": test_type,
                "Safety Limit": safety_limit, "Deflection": deflection, "Spring Rate": spring_rate
            }
            
            if st.button("Update Parameters"):
                st.session_state.parameters.update(parameters)
                st.success("Parameters updated!")
            
            st.subheader("Current Parameters")
            st.json(st.session_state.parameters)
            
            if st.button("Generate Sequence"):
                if not api_key:
                    st.error("Please provide an API key")
                elif not st.session_state.parameters:
                    st.error("Please update parameters first")
                else:
                    with st.spinner("Generating test sequence..."):
                        df = call_custom_api("Generate sequence", st.session_state.parameters, api_key)
                        if not df.empty:
                            st.success("Successfully generated test sequence!")
                            st.dataframe(df)
                            csv = df.to_csv(index=False)
                            st.download_button("Download CSV", data=csv, file_name="test_sequence.csv", mime="text/csv")
    
    with st.sidebar.expander("Command Reference", False):
        for cmd, desc in COMMANDS.items():
            st.write(f"**{cmd}**: {desc}")

if __name__ == "__main__":
    main()