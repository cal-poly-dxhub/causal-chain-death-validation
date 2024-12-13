# causal-chain-death-validation

This project is designed in collaboration with the State of Michigan Department of Health and the CDC.
The purpose is to assist doctors in creating valid causal chains of conditions that lead to the death of a patient.
With this application, doctors can input a chain of conditions, and optionally *codeify* them (an LLM will condition
the input terminology that the doctor uses to increase accuracy) before running the chain against a Neptune Graph
Database that hosts the source of truth ruleset that defines the requirements for causal chains to be valid.

**Source of Truth used:** 
https://www.cdc.gov/nchs/nvss/manuals/2024/2c-2024-raw.html
Another useful link: https://www.cdc.gov/nchs/data/dvs/2c2009.pdf

**Architecture**
![alt text](https://github.com/cal-poly-dxhub/causal-chain-death-validation/blob/main/michArch.png)

**Steps to run:**

1. Initialize EC2 that is hosting embeddings model:
     - start the **pubmed** EC2 (i-01621a144abf33487)
     - run **cd pubmed**
     - run **uvicorn webservice:app --host "0.0.0.0" --port 8000 --reload**
     - after around 1 minute the EC2 will say *Application Startup Complete*

2. If using the streamlit interface, run **streamlit run testApi.py**

3. Test your chain of conditions.


Example API Call in Python:

```
baseUrl = r"https://jeczjol1g9.execute-api.us-west-2.amazonaws.com/test/"
endpoint = "recommendations"
payload = {
   'conditions': conditions_dict,
   'wantCodeify': '0' 
}
full_url = f"{baseUrl}{endpoint}"
response = requests.post(full_url, json=payload)
```

Payload Example:

{'conditions': {'underlying condition': 'diabetes', 'condition 3': 'obesity', 'condition 2': 'high blood pressure', 'main condition': 'myocardial infarction'}, 'wantCodeify': '0'}

underlying (4), 3, 2, main (1) where the main condition is the final disease or condition resulting in the death of the patient, and the preceding conditions are all causes of the next.
So the underlying condition causes condition 3, condition 3 causes condition 2, and condition 2 causes the main condition.
'1' to codeify the conditions, '0' to not codeify the conditions.
