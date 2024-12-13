import os
import pickle
import time
import csv
import boto3
import txtai




# I believe this has been replaced by testtxt.py





# Initialize S3 client
s3 = boto3.client('s3')

# timing information
t = []
def rt():
    t.append(time.perf_counter())
def mt():
    return round(t[-1] - t[-2], 3)

rt()
INDEX_DATA_PATH = 'embeddings_index_data'
os.makedirs(INDEX_DATA_PATH, exist_ok=True)
CODE_DICT_PATH = 'code_dict.pkl'

# Load ICD mortality data and create embeddings index
if os.path.exists(INDEX_DATA_PATH) and os.path.exists(CODE_DICT_PATH):
    rt()
    # Initialize embeddings with the local path
    embeddings = txtai.Embeddings(path="neuml/pubmedbert-base-embeddings", content=True)
    
    # Load the saved index
    embeddings.load(INDEX_DATA_PATH)
    
    with open(CODE_DICT_PATH, 'rb') as f:
        code_dict = pickle.load(f)
    rt()
    print(mt(), "Loaded saved embeddings index and code dictionary")
else:
    rt()
    code_dict = {}
    # Open the CSV file
    with open(r'2allvalid2020.csv', newline='') as csvfile:
        csv_reader = csv.reader(csvfile)
        for row in csv_reader:
            code = row[1].replace('.', '')
            title = row[2]
            code_dict[title] = code
    rt()
    print(mt(), "Imported ", len(code_dict), " titles and codes from allvalid2020 icd mortality data.")

    # Index the data
    embeddings.index(code_dict.keys())
    rt()
    print(mt(), "Created index from keys")

    # Save the embeddings index and code_dict
    embeddings.save(INDEX_DATA_PATH)
    with open(CODE_DICT_PATH, 'wb') as f:
        pickle.dump(code_dict, f)
    print("Saved embeddings index and code dictionary")

# Download table CSV files from S3
tablePaths = [
    'MortemEncodingsFiles/data/2024/TableA.csv', 
    'MortemEncodingsFiles/data/2024/TableB.csv',
    'MortemEncodingsFiles/data/2024/TableC1.csv', 
    'MortemEncodingsFiles/data/2024/TableC2.csv',
    'MortemEncodingsFiles/data/2024/TableC3.csv'
]
local_table_dir = 'data/tables'
os.makedirs(local_table_dir, exist_ok=True)
for s3_file_path in tablePaths:
    local_file_path = os.path.join(local_table_dir, os.path.basename(s3_file_path))
    s3.download_file("cod-chains-data", s3_file_path, local_file_path)

def checkSimilar(term):
    res = {}
    rt()
    result = embeddings.search(term)
    rt()
    t = mt()
    csv_contents = read_csv_files(tablePaths)
    for x in range(len(result)):
        title = result[x]['text']
        if title in code_dict:
            code = code_dict[title]
            file_path = find_csv_file_for_code(code, csv_contents)
            if file_path:
                res[result[x]['score']] = (title, code, file_path)
    embeddingsResult = {
        "invocationTime": t,
        "result": res
    }
    return embeddingsResult

def read_csv_files(file_paths):
    csv_contents = {}
    for file_path in file_paths:
        local_file_path = os.path.join(local_table_dir, os.path.basename(file_path))
        with open(local_file_path, newline='') as csvfile:
            csv_reader = csv.reader(csvfile)
            codes = [row[0] for row in csv_reader]
            csv_contents[local_file_path] = codes
    return csv_contents

def is_prefix(code, code_list):
    for entry in code_list:
        if entry.startswith(code):
            return True
    return False

def find_csv_file_for_code(code, csv_contents):
    for file_path, codes in csv_contents.items():
        if is_prefix(code, codes):
            return os.path.basename(file_path)
    return None
