# causal-chain-death-validation


# Collaboration
Thanks for your interest in our solution.  Having specific examples of replication and cloning allows us to continue to grow and scale our work. If you clone or download this repository, kindly shoot us a quick email to let us know you are interested in this work!

[wwps-cic@amazon.com] 

# Disclaimers

**Customers are responsible for making their own independent assessment of the information in this document.**

**This document:**

(a) is for informational purposes only, 

(b) represents current AWS product offerings and practices, which are subject to change without notice, and 

(c) does not create any commitments or assurances from AWS and its affiliates, suppliers or licensors. AWS products or services are provided “as is” without warranties, representations, or conditions of any kind, whether express or implied. The responsibilities and liabilities of AWS to its customers are controlled by AWS agreements, and this document is not part of, nor does it modify, any agreement between AWS and its customers. 

(d) is not to be considered a recommendation or viewpoint of AWS

**Additionally, all prototype code and associated assets should be considered:**

(a) as-is and without warranties

(b) not suitable for production environments

(d) to include shortcuts in order to support rapid prototyping such as, but not limitted to, relaxed authentication and authorization and a lack of strict adherence to security best practices

**All work produced is open source. More information can be found in the GitHub repo.**

## Authors
- Noor Dhaliwal - rdhali07@calpoly.edu



## Solution Overview
This project is designed in collaboration with the State of Michigan Department of Health and the CDC.
The purpose is to assist doctors in creating valid causal chains of conditions that lead to the death of a patient.
With this application, doctors can input a chain of conditions, and optionally *codeify* them (an LLM will condition
the input terminology that the doctor uses to increase accuracy) before running the chain against a Neptune Graph
Database that hosts the source of truth ruleset that defines the requirements for causal chains to be valid.

**Source of Truth used:** 
https://www.cdc.gov/nchs/nvss/manuals/2024/2c-2024-raw.html
Another useful link: https://www.cdc.gov/nchs/data/dvs/2c2009.pdf

**Architecture**
![alt text](https://github.com/cal-poly-dxhub/causal-chain-death-validation/blob/main/michArch2.png)

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
