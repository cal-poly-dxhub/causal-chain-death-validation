import os
import txtai
import boto3
import csv
import time
import json

# Initialize txtai embeddings
startprept = time.time()
embeddings = txtai.Embeddings(path="neuml/pubmedbert-base-embeddings", content=True)

# Load dataset into a dictionary
code_dict = {}
with open(r'2allvalid2020.csv', newline='') as csvfile:
    csv_reader = csv.reader(csvfile)
    for row in csv_reader:
        code = row[1].replace('.', '')
        title = row[2]
        code_dict[title] = code
print(f"Imported {len(code_dict)} titles and codes from the allvalid2020 dataset.")
embeddings.index(code_dict.keys())
readyt = time.time()
print(f"Indexing complete. Ready to query after {readyt-startprept} seconds.")

# CSV file paths
tablePaths = [
    '/home/ec2-user/data/tables/TableA.csv', 
    '/home/ec2-user/data/tables/TableB.csv',
    '/home/ec2-user/data/tables/TableC1.csv', 
    '/home/ec2-user/data/tables/TableC2.csv',
    '/home/ec2-user/data/tables/TableC3.csv'
]

# AWS Bedrock Reranking Setup
bedrock = boto3.client('bedrock-runtime', region_name="us-west-2")

def rerank_text(text_query, text_sources, num_results):
    request_body = {
        "query": text_query,
        "documents": [doc["inlineDocumentSource"]["textDocument"]["text"] for doc in text_sources],
        "top_n": num_results,
        "api_version": 2
    }
    
    response = bedrock.invoke_model(
        modelId="cohere.rerank-v3-5:0",
        body=json.dumps(request_body)
    )
    
    response_body = json.loads(response['body'].read())
    
    # Transform the response to match your expected format
    results = []
    for idx, result in enumerate(response_body['results']):
        results.append({
            'index': result['index'],
            'score': result['relevance_score']
        })
    
    return results

# Main function with reranking and logging
def checkSimilar(term):
    t1 = time.time()
    res = {}
    log_file = "search_results_log.txt"
    
    with open(log_file, "w") as log:
        log.write(f"Query: {term}\n\n")
        
        # Step 1: Retrieve initial search results from txtai
        initial_results = embeddings.search(term)  # Fetch top 10 results
        
        log.write("Original Results (txtai):\n")
        for idx, result in enumerate(initial_results):
            log.write(f"{idx+1}. {result['text']}\n")
        log.write("\n")
        
        # Step 2: Prepare documents for reranking
        text_sources = [
            {
                "type": "INLINE",
                "inlineDocumentSource": {
                    "type": "TEXT",
                    "textDocument": {"text": result["text"]}
                }
            } 
            for result in initial_results
        ]
        
        # Step 3: Perform reranking
        reranked_results = rerank_text(term, text_sources,len(text_sources))
        
        log.write("Reranked Results (AWS Bedrock):\n")
        for idx, entry in enumerate(reranked_results):
            original_index = entry["index"]  # Original index in initial results
            title = initial_results[original_index]["text"]
            log.write(f"{idx+1}. {title} (Score: {entry['score']})\n")
        log.write("\n")
    
    # Step 4: Read CSV files
    csv_contents = read_csv_files(tablePaths)

    # Step 5: Process the reranked results
    for entry in reranked_results:
        index = entry["index"]  # Original index in the initial results
        title = initial_results[index]["text"]
        score = entry["score"]  # New reranked score
        
        if title in code_dict:
            code = code_dict[title]
            file_path = find_csv_file_for_code(code, csv_contents)
            if file_path:
                res[score] = (title, code, file_path)
    
    t = time.time() - t1
    return {"invocationTime": t, "result": res}

# Function to read CSV files and store their contents in a dictionary
def read_csv_files(file_paths):
    csv_contents = {}
    for file_path in file_paths:
        with open(file_path, newline='') as csvfile:
            csv_reader = csv.reader(csvfile)
            codes = [row[0] for row in csv_reader]  # Read all codes
            csv_contents[file_path] = codes
    return csv_contents

# Function to check if the code is a prefix of any code in the list
def is_prefix(code, code_list):
    return any(entry.startswith(code) for entry in code_list)

# Function to check which CSV file contains the code
def find_csv_file_for_code(code, csv_contents):
    for file_path, codes in csv_contents.items():
        if is_prefix(code, codes):
            return os.path.basename(file_path)
    return None
