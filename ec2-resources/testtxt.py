import os
import txtai
import boto3
import csv
import time


startprept = time.time()
embeddings = txtai.Embeddings(path="neuml/pubmedbert-base-embeddings", content=True)

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

tablePaths = ['/home/ec2-user/data/tables/TableA.csv', '/home/ec2-user/data/tables/TableB.csv',
              '/home/ec2-user/data/tables/TableC1.csv', '/home/ec2-user/data/tables/TableC2.csv',
              '/home/ec2-user/data/tables/TableC3.csv']

def checkSimilar(term):
    t1 = time.time()
    res = {}

    result = embeddings.search(term)


    csv_contents = read_csv_files(tablePaths)

    for x in range(len(result)):
        title = result[x]['text']
        if title in code_dict:
            code = code_dict[title]
            file_path = find_csv_file_for_code(code, csv_contents)
            if file_path:
                res[result[x]['score']] = (title, code, file_path)
    
    t = time.time() - t1

    embeddingsResult = {
        "invocationTime": t,
        "result": res
    }

    return embeddingsResult


    

# Function to read CSV files and store their contents in a dictionary
def read_csv_files(file_paths):
    csv_contents = {}
    for file_path in file_paths:
        with open(file_path, newline='') as csvfile:
            csv_reader = csv.reader(csvfile)
            # Read all codes into a list
            codes = [row[0] for row in csv_reader]
            csv_contents[file_path] = codes
    return csv_contents

# Function to check if the code is a prefix of any code in the list
def is_prefix(code, code_list):
    for entry in code_list:
        if entry.startswith(code):
            return True
    return False

# Function to check which CSV file contains the code
def find_csv_file_for_code(code, csv_contents):
    for file_path, codes in csv_contents.items():
        if is_prefix(code, codes):
            return os.path.basename(file_path)
    return None
