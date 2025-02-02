import json
import urllib.parse
import requests
import boto3
import time
import os
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

brt = boto3.client(service_name='bedrock-runtime')

def lambda_handler(event, context):
    logger.info(f"Received event: {json.dumps(event)}")
    
    http_method = event.get('httpMethod')
    
    if http_method == 'GET':
        return handle_get_request(event)
    elif http_method == 'POST':
        return handle_post_request(event)
    else:
        return {
            'statusCode': 405,
            'body': json.dumps('Method Not Allowed')
        }

def handle_get_request(event):
    s1 = time.time()
    query_params = event.get('queryStringParameters', {})
    
    # Decoding the 'conditions' JSON string from URL encoding
    conditions_query = query_params.get('conditions', '{}')  # Default to empty dictionary
    wantCodeify = query_params.get('wantCodeify','0')
    decoded_conditions = urllib.parse.unquote(conditions_query)
    decoded_conditions = decoded_conditions.replace('+', ' ')
    conditions_dict = json.loads(decoded_conditions)
    
    logger.info("Before validate reached")
    
    result = validate(conditions_dict, wantCodeify)
    
    transactionResponse = {
        'conditions': conditions_dict,  # Include decoded conditions in the response
        'result': result,
        'apiInvocationTime': f"{(time.time()-s1)} seconds",
    }

    responseObject = {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(transactionResponse)
    }

    return responseObject

def handle_post_request(event):
    try:
        # Parse the JSON body of the POST request
        body = json.loads(event['body'])
        
        # Extract conditions and wantCodeify from the body
        conditions_dict = body.get('conditions', {})
        wantCodeify = body.get('wantCodeify', '0')
        
        logger.info(f"Received POST request with conditions: {conditions_dict}")
        
        # Use the same validate function as in GET
        result = validate(conditions_dict, wantCodeify)
        
        transactionResponse = {
            'conditions': conditions_dict,
            'result': result,
            'apiInvocationTime': f"{time.time()} seconds",
        }
        
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps(transactionResponse)
        }
    except json.JSONDecodeError:
        logger.error("Invalid JSON in POST body")
        return {
            'statusCode': 400,
            'body': json.dumps('Invalid JSON in request body')
        }
    except Exception as e:
        logger.error(f"Error processing POST request: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps('Internal server error')
        }


def validate(conditions_dict, wantCodeify="0"):
    
    start = time.time()
    # first call LLM to 'codeify' the input conditions

    logs = "***LOGS***\n\n"
    
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
    # then we will run the 'codeified' conditions against pubmedbert

    results = []
    titles = []

    embeddingsResults = {}

    print("after codeified reached")

    for cond in codeifiedConds:
        embeddingsURL = formatURL(cond)
        print(embeddingsURL)
        embeddingsResults[cond] = requests.get(embeddingsURL).json()
        data = embeddingsResults[cond]
        print(data)
        invtime = data['invocationTime']
        logs = logs + f"PubMedBert Invocation Time: {invtime}\n\n"
        logs = logs + f"Embeddings Results: {data}\n\n"

        result_dict = data['result']

        filtered_result_dict = {k: v for k, v in result_dict.items() if float(k) >= 0.05} #good

        results.append(filtered_result_dict)
        titles.append(cond)

    print("after embeddings request made")
    
    if len(results) == 0:
        logs = logs + "No results met similarity threshold.\n\n"
    else:
        logs = logs + f"Results After Filter: {results}\n\n"
    # then check to make sure that the conditions pass stage one from response

    newlist = []
    icds = ['' for n in range(len(results))]
    valid_tablesA = ['TableA.csv', 'TableC1.csv']
    valid_tablesB = ['TableA.csv', 'TableB.csv', 'TableC1.csv', 'TableC2.csv']
    invalid_codes_file = 'invalidCodes.txt'
    invalid_codes = set()

    # Read the invalid codes from the text file
    with open(invalid_codes_file, 'r') as file:
        for line in file:
            invalid_codes.add(line.strip())

    # Iterate through the list of result dictionaries
    for i, result_dict in enumerate(results):
        # Determine the correct table to check based on the position in the list

        # Check each key-value pair in the current result dictionary
        for key, valueList in result_dict.items():
        # key = 0.8447627425193787
        # valueList = ['Acute subendocardial myocardial infarction', 'I214', 'TableA.csv']

            # If the valueList[2] matches one of the valid tables and the code is not in the invalid codes, add the key-value pair to the new list
            if i == len(results) - 1:
                if valueList[2] in valid_tablesA and valueList[1] not in invalid_codes and valueList[1]:
                    newlist.append({key: valueList})
                    icds[i] = valueList[1]
                    break
                else:
                    logs = logs + f"STAGE 1: Underlying Cause {valueList} not in {valid_tablesA} or is in invalid codes, filtered out.\n\n"
            else:
                if valueList[2] in valid_tablesB and valueList[1]:
                    newlist.append({key: valueList})
                    icds[i] = valueList[1]
                    break
                else:
                    logs = logs + f"STAGE 1: {valueList[0]} not in {valid_tablesB}, filtered out.\n\n"

    logs = logs + f"After STAGE 1 + highest similarity: {newlist}\n\n"
    logs = logs + f"ICDs: {icds}\n\n"


    # then call the graph db to check stage 2
    
    stage2res = stageTwo(icds[::-1], titles[::-1])

    print("after stage 2 graph neptune done")

    # then call LLM to convey result to user
    formattedCodefied = format_conditions_dict(codeifiedConds)
    conveyedResponse = convey(formattedCodefied, stage2res)


    end = time.time()

    responseObject = {
        'validationTime':(end-start),
        'originalInputConditions':conditions_dict,
        'codefiedConditions':formattedCodefied,
        # 'embeddingsURL':embeddingsURL,
        'logs':logs,
        'stage2result':stage2res,
        'conveyedResponse':conveyedResponse
    }

    return responseObject


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


def convey(conds,result):
    body = json.dumps({
    "max_tokens":256,
    "messages": [{"role": "user", "content": f"""
                    Given an input chain of medical health conditions
                    that a patient died by, and a validation result,
                    provide some recommendations and convey the validation
                    result back with those recommendations to make the chain
                    better for a more accurate death certificate, if you deem
                    a higher accuracy to be neccessary. Note that the validation
                    result determines whether or not the chain of conditions
                    is a valid causal chain, but please also give a short recommendation
                    on how to make the chain better for a death certificate. For example,
                    if the input chain is something like 'acute myocardial infarction' and
                    nothing else, recommend that the user put a valid underlying condition.
                    Here is the input chain: {conds}. Here is the validation result: {result}.
                    Remember, I need a short response that simply conveys and recommends if needed.
                    """}],
    "anthropic_version": "bedrock-2023-05-31"
    })

    llmres = brt.invoke_model(body=body, modelId="anthropic.claude-3-haiku-20240307-v1:0")
    streaming_body = llmres['body']
    content = streaming_body.read().decode('utf-8')
    data_dict = json.loads(content)

    return data_dict['content'][0]['text']


def formatURL(cond):
    encodedCond = urllib.parse.quote(cond)
    base_url = f"http://10.0.29.235:8000/embeddings/{encodedCond}"
    return base_url


def stageTwo(icds, titles):
    if len(icds) == 1:
        return "VALID" if icds[0] else "INVALID - INVALID CAUSE"
    elif len(icds) == 0:
        return "NO ICDS TO BE VALIDATED"
    else:
        # First, check all ICDs for emptiness
        for idx, code in enumerate(icds):
            if code == '':
                return f"CONDITION @ POS {idx} (0-INDEXED) IS '', INVALID ENTRY"
        
        # Now validate causal relationships between consecutive pairs
        for i in range(len(icds) - 1):
            current_effect = icds[i+1]
            current_cause = icds[i]
            
            # Check if current_cause causes current_effect (via checkRelationship(effect, cause))
            if not checkRelationship(current_effect, current_cause):
                # If not, check if swapping would fix it (i.e., check if the inverse relationship holds)
                swapped_effect = icds[i]
                swapped_cause = icds[i+1]
                if checkRelationship(swapped_effect, swapped_cause):
                    # Swap is possible, but need to validate compatibility with neighbors
                    error_msg = None
                    # Check previous relationship (if not first element)
                    if i > 0:
                        prev_effect = icds[i+1]  # After swap, this becomes the new current_cause
                        prev_cause = icds[i-1]   # Previous cause remains the same
                        if not checkRelationship(prev_effect, prev_cause):
                            error_msg = f"ATTEMPTED SWAP: {titles[i]} WITH {titles[i+1]}; BUT {titles[i-1]} CANNOT CAUSE {titles[i+1]}"
                    
                    # Check next relationship (if not last pair)
                    if i < len(icds) - 2 and not error_msg:
                        next_effect = icds[i+2]
                        next_cause = icds[i]     # After swap, this becomes the new current_effect
                        if not checkRelationship(next_effect, next_cause):
                            error_msg = f"ATTEMPTED SWAP: {titles[i]} WITH {titles[i+1]}; BUT {titles[i]} CANNOT CAUSE {titles[i+2]}"
                    
                    if error_msg:
                        return error_msg
                    else:
                        return f"SWAP {titles[i]} WITH {titles[i+1]}"
                else:
                    return f"{titles[i+1]} CANNOT CAUSE {titles[i]} AND SWAP NOT POSSIBLE"
        return "VALID"


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


def checkRelationship(address, subaddress):
    url = "https://db-neptune-1-newchains.cluster-cmh9pzew6est.us-west-2.neptune.amazonaws.com:8182/openCypher"
    relationshipExists = False
    
    query = f"MATCH (n)-[r]->(m) WHERE id(n) = '{address}' AND id(m) = '{subaddress}' RETURN r"
    
    data = {"query": query}
    
    response = requests.post(url, data=data)
    
    # Check if the request was successful
    if response.status_code == 200:
        print("Query successful.")
        response_json = response.json()
        # Print the response data
        print(response_json)
        
        # Check the length of the results list
        if len(response_json['results']) > 0:
            relationshipExists = True
        else:
            relationshipExists = False
    else:
        print("Failed to execute query.")
        print("Status code:", response.status_code)
        print("Response:", response.text)
        
    return relationshipExists