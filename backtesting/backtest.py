import time
import boto3
import requests
import csv
import ast
import json
import urllib.parse


start = time.time()

brt = boto3.client(service_name='bedrock-runtime')

def formatURL(cond):
    encodedCond = urllib.parse.quote(cond)
    base_url = f"http://10.0.29.235:8000/embeddings/{encodedCond}"
    return base_url


def codeify(condition):
    body = json.dumps({
    "max_tokens":256,
    "messages": [{"role": "user", "content": f"""
                    Take this input condition, which is in the doctor's natural
                    language, and try to make it more medically 'accurate'. I
                    want this condition to be mapped somewhat closely
                    to the official ICD-10 Mortality Data title that this
                    specific input condition would correspond to. However, keep the
                    new title as close as possible to the input title - barely make
                    any change to the input title that is not necessary.
                    If the input is something totally out of wack, like 'ooga booga,'
                    just return 'INVALID.' If it is just a very general and not specific
                    condition, maybe just append 'unspecified' to the end of the condition.
                    If a big change is needed, I would rather have the innacurate
                    input title instead. A small change, such as going from 
                    INPUT: 'type 2 diabetes mellitus' to OUTPUT: 'non insulin 
                    dependent diabetes mellitus'
                    would be the level of change I am looking to get from you. 
                    Respond with nothing else but the output condition. Here is the input
                    condition that I want you to map to an ICD title: {condition}
                    """}],
    "anthropic_version": "bedrock-2023-05-31"
    })

    llmres = brt.invoke_model(body=body, modelId="anthropic.claude-3-haiku-20240307-v1:0")
    streaming_body = llmres['body']
    content = streaming_body.read().decode('utf-8')
    data_dict = json.loads(content)

    return data_dict['content'][0]['text']


def checkRelationship(address, subaddress):
    url = "https://db-neptune-1-newchains.cluster-cmh9pzew6est.us-west-2.neptune.amazonaws.com:8182/openCypher"
    relationshipExists = False
    
    query = f"MATCH (n)-[r]->(m) WHERE id(n) = '{address}' AND id(m) = '{subaddress}' RETURN r"
    
    data = {"query": query}
    
    response = requests.post(url, data=data)
    
    # Check if the request was successful
    if response.status_code == 200:
        response_json = response.json()
        if len(response_json['results']) > 0:
            relationshipExists = True
        else:
            relationshipExists = False
    else:
        print("Failed to execute query.")
        print("Status code:", response.status_code)
        print("Response:", response.text)
        
    return relationshipExists


def stageTwo(icds):
    icds = reversed(icds)
    if len(icds) == 1:
        if icds[0] != '':
            return ["VALID",'']
        else:
            return ["INVALID",'']
    elif len(icds) == 0:
        return ["INVALID",'']
    else:
        for i in range(len(icds) - 1):
            if icds[i] == '':
                return ["INVALID",'']
            evalOrder = f"Checking if {icds[i]} causes {icds[i+1]}"
            print(evalOrder)
            if not checkRelationship(icds[i+1], icds[i]):
                return ["INVALID",evalOrder]
        return ["VALID",evalOrder]




def validate(conditions_dict, wantCodeify="0"):
        
    preprocessedCondsVals = (list(conditions_dict.values()))
    preprocessedCondsKeys = (list(conditions_dict.keys()))
    if preprocessedCondsKeys[0].lower() == 'underlying condition':
        preprocessedCondsVals = list(reversed(preprocessedCondsVals))

    codeifiedConds = []
    if wantCodeify == "1":
        for condition in preprocessedCondsVals:
            codeifiedConds.append((codeify(condition)))
    else:
        for condition in preprocessedCondsVals:
            codeifiedConds.append((condition))

    results = []

    embeddingsResults = {}


    for cond in codeifiedConds:
        embeddingsURL = formatURL(cond)
        print(embeddingsURL)
        embeddingsResults[cond] = requests.get(embeddingsURL).json()
        data = embeddingsResults[cond]

        result_dict = data['result']

        filtered_result_dict = {k: v for k, v in result_dict.items() if float(k) >= 0.6} #good

        results.append(filtered_result_dict)


    newlist = []
    icds = ['' for n in range(len(results))]
    valid_tablesA = ['TableA.csv', 'TableC1.csv']
    valid_tablesB = ['TableA.csv', 'TableB.csv', 'TableC1.csv', 'TableC2.csv']
    invalid_codes_file = 'invalidCodes.txt'
    invalid_codes = set()

    with open(invalid_codes_file, 'r') as file:
        for line in file:
            invalid_codes.add(line.strip())

    for i, result_dict in enumerate(results):

        for key, valueList in result_dict.items():
        # key = 0.8447627425193787
        # valueList = ['Acute subendocardial myocardial infarction', 'I214', 'TableA.csv']

            if i == len(results) - 1:
                if valueList[2] in valid_tablesA and valueList[1] not in invalid_codes and valueList[1]:
                    newlist.append({key: valueList})
                    icds[i] = valueList[1]
                    break
            else:
                if valueList[2] in valid_tablesB and valueList[1]:
                    newlist.append({key: valueList})
                    icds[i] = valueList[1]
                    break
    
    return stageTwo(icds[::-1])

results = {}
counter = 0
with open('cod_codes.txt', mode='r') as file:
    lines = file.readlines()

validCount = 0
totalCount = 0

for index,line in enumerate(lines):
    totalCount += 1
    if index == 10:
        break

    codesList = ast.literal_eval(line.strip()) # read the list from the line string

    print(f"Row {index+1} : List: {codesList}")

    codedict = {}

    # main 2 3 underlying
    for ind in range(len(codesList)):
        if ind == (len(codesList)-1):
            codedict['underlying condition'] = codesList[ind]
        else:
            codedict[str(ind)] = codesList[ind]

    print(f"Dict: {codedict}\n")

    result = validate(codedict)
    results[index] = result
    if result[0] == 'VALID':
        validCount += 1
    




with open('testOutput.csv', mode='w', newline='', encoding='utf-8') as out:
    writer = csv.writer(out)
    writer.writerow(['Index', 'Validation Result', 'Codes List', 'Code Dict', 'EvalOrder'])

    for ind in results.keys():  # Fix: add parentheses after 'keys'
        r = results[ind]
        writer.writerow([ind, r[0], codesList, codedict,r[1]])
        


print(validCount)
print(totalCount)

end = time.time()
print(f"Time taken: {end - start} seconds")



