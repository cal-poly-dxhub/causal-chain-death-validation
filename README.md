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
