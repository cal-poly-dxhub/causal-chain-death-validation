import streamlit as st
import streamlit_authenticator as stauth
import requests
import json
import urllib
import yaml
from yaml.loader import SafeLoader



def main():
    with open('config.yaml') as file:
        config = yaml.load(file, Loader=SafeLoader)

    # Pre-hashing all plain text passwords once
    stauth.Hasher.hash_passwords(config['credentials'])

    authenticator = stauth.Authenticate(
        config['credentials'],
        config['cookie']['name'],
        config['cookie']['key'],
        config['cookie']['expiry_days']
    )

    try:
        authenticator.login()
    except Exception as e:
        st.error(e)
    
    if st.session_state['authentication_status']:
        with st.sidebar:
            authenticator.logout()
        st.title("Testing frontend for API implementation of Mortem Matters Project")

        # Check for 'conditions' instead of 'condition'
        if 'conditions' not in st.session_state:
            st.session_state.conditions = [""]
            st.session_state.conditions_dict = {}
            st.session_state.wantCodeify = "0"
            st.session_state.result = {}
            st.session_state.flag = 0
        if st.session_state.wantCodeify == "1":
            st.write("LLM WILL CODEIFY INPUT CONDITIONS")
        if st.session_state.flag == 1:
            st.write(st.session_state.result['result']['stage2result'])
            st.write(st.session_state.result['result']['conveyedResponse'])
            if(st.button("Show JSON")):
                st.write(st.session_state.result)

        # Display input fields for all conditions
        for i in range(len(st.session_state.conditions)):
            if i == 0:
                st.session_state.conditions[i] = st.text_input("IMMEDIATE CAUSE (Final disease or condition resulting in death)", 
                                                            value=st.session_state.conditions[i], 
                                                            key=f"cond_{i}")
            else:
                st.session_state.conditions[i] = st.text_input(f"Condition #{i+1}: What caused the above condition?", 
                                                            value=st.session_state.conditions[i], 
                                                            key=f"cond_{i}")

        # Sidebar buttons for adding and finalizing conditions
        with st.sidebar:
            if st.button("Add Condition"):
                # Append an empty string and force rerun to immediately reflect the new input field
                st.session_state.conditions.append("")
                st.rerun()
            
            if st.button("Should an LLM condition your inputs for possibly higher accuracy? Click if Yes"):
                st.session_state.wantCodeify = "1"
                st.rerun()

            if st.button("Done Adding Conditions"):
                # Convert conditions into the required dictionary format
                st.session_state.conditions_dict = format_conditions_dict(st.session_state.conditions)

                st.session_state.result = validate(st.session_state.conditions_dict, st.session_state.wantCodeify)
                st.session_state.flag = 1
                st.rerun()

            if st.session_state.flag == 1:
                st.button('Restart', on_click=clear_cache)

            st.write("Conditions recorded:", st.session_state.conditions_dict)
    
    elif st.session_state['authentication_status'] is False:
        st.error('Username/password is incorrect')

def clear_cache():
    keys = list(st.session_state.keys())
    for key in keys:
        st.session_state.pop(key)

def format_conditions_dict(conditions):
    if len(conditions) == 1:
        return {"main condition": conditions[0]}

    condition_dict = {}
    for i, condition in enumerate(conditions):
        if i == 0:
            condition_dict["main condition"] = condition
        elif i == len(conditions) - 1:
            condition_dict["underlying condition"] = condition
        else:
            condition_dict[f"condition {i+1}"] = condition
    
    condition_dict = dict(reversed(list(condition_dict.items())))
    return condition_dict


def validate(conditions_dict, wantCodeify):
    baseUrl = r"https://jeczjol1g9.execute-api.us-west-2.amazonaws.com/test/"
    endpoint = "recommendations"
    
    # Prepare payload as JSON for POST request
    payload = {
        'conditions': conditions_dict,
        'wantCodeify': wantCodeify
    }
    
    # Construct the full URL
    full_url = f"{baseUrl}{endpoint}"
    
    print("Making POST request to:", full_url)  # Log the full URL
    print("Payload:", payload)  # Log the payload
    
    try:
        # Make the POST request with the JSON payload
        response = requests.post(full_url, json=payload)
        print("Response Status Code:", response.status_code)
        print("Response Text:", response.text)  # Log the response text
        
        # Check the response status and handle errors
        if response.status_code == 200:
            result = response.json()
            return result
        else:
            st.error(f"Error: API request failed with status code {response.status_code}")
            return {"error": f"API request failed with status code {response.status_code}"}
    
    except requests.RequestException as e:
        st.error(f"Error: {str(e)}")
        return {"error": str(e)}




if __name__ == "__main__":
    main()