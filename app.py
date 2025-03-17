import streamlit as st
import pandas as pd
import requests
import json
import re

def call_custom_api(instruction, api_key):
    """
    Calls the custom API endpoint with proper Markdown cleaning
    and enhanced error handling
    """
    url = "https://chat01.ai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    messages = [
        {
            "role": "system",
            "content": (
                "You are an AI that interprets instructions for a force testing system. "
                "The system uses these possible commands: ZF, TH, FL(P), Mv(P), Scrag, Fr(P), TD. "
                "Generate a structured test sequence ONLY if relevant. Each entry should have:\n"
                "CMD, Description, Condition, Unit, and Tolerance.\n"
                "Output ONLY RAW JSON containing a list of objects. "
                "DO NOT USE ANY MARKDOWN FORMATTING or code blocks. "
                "Just the pure JSON array with no additional text or explanations."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Instruction:\n{instruction}\n\n"
                "Return JSON array of objects with fields: "
                "CMD, Description, Condition, Unit, Tolerance. "
                "Only the JSON, no other text or formatting."
            ),
        },
    ]

    payload = {
        "model": "gpt-4o",
        "messages": messages,
        "temperature": 0
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        
        response_json = response.json()
        
        # Extract message content
        if not response_json.get('choices'):
            st.error("No choices in API response")
            return pd.DataFrame()
            
        message = response_json['choices'][0].get('message', {})
        raw_content = message.get('content', '')
        
        # Clean Markdown formatting using regex
        cleaned_content = re.sub(r'^```json|```$', '', raw_content, flags=re.MULTILINE)
        cleaned_content = cleaned_content.strip()
        
        # Debugging output (can be commented out)
        st.session_state.last_raw_response = raw_content
        st.session_state.last_cleaned_content = cleaned_content

        # Parse JSON
        data = json.loads(cleaned_content)
        
        if isinstance(data, list):
            return pd.DataFrame(data)
        return pd.DataFrame()

    except requests.exceptions.HTTPError as http_err:
        st.error(f"HTTP Error ({response.status_code}): {http_err}")
        if response.status_code == 401:
            st.error("Authentication error - check your API key")
        elif response.status_code == 429:
            st.error("Rate limit exceeded - try again later")
        return pd.DataFrame()
    except json.JSONDecodeError as e:
        st.error(f"JSON Parsing Error: {str(e)}")
        st.error(f"Cleaned content that failed:\n{cleaned_content}")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")
        return pd.DataFrame()

def main():
    st.title("AI-Powered Test Sequence Generator")
    st.markdown("Transform natural language instructions into structured test sequences")

    # API Key Input
    api_key = st.text_input("API Key", type="password", help="Enter your Chat01.ai API key")

    # Instruction Input
    instruction = st.text_area(
        "Test Instruction", 
        placeholder="E.g.: 'Create a compression test sequence with 5 steps...'",
        height=150
    )

    # Debugging section (can be hidden)
    with st.expander("Debug Info", False):
        if 'last_raw_response' in st.session_state:
            st.write("Last Raw Response:")
            st.code(st.session_state.last_raw_response)
            st.write("Last Cleaned Content:")
            st.code(st.session_state.last_cleaned_content)

    if st.button("Generate Sequence"):
        if not api_key:
            st.error("Please provide an API key")
            return
        if not instruction:
            st.error("Please enter a test instruction")
            return
            
        with st.spinner("Generating test sequence..."):
            df = call_custom_api(instruction, api_key)
            
        if not df.empty:
            st.success("Successfully generated test sequence!")
            st.dataframe(df.style.highlight_max(axis=0))  # Removed use_container_width parameter
            
            # CSV Download
            csv = df.to_csv(index=False)
            st.download_button(
                "Download CSV",
                data=csv,
                file_name="test_sequence.csv",
                mime="text/csv",
                help="Download generated sequence as CSV file"
            )
        else:
            st.warning("No valid sequence generated. Try refining your instruction.")

if __name__ == "__main__":
    main()