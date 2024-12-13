import csv

# Define the list to hold the COD codes
cod_codes = []

# Open the CSV file
with open('deaths2018_2022.csv', 'r') as file:
    reader = csv.DictReader(file)
    
    # Iterate over each row in the CSV and limit to 10,000 rows
    for index, row in enumerate(reader):
        if index >= 10000:
            break
        
        codes = []
        
        # Add the cod_1 to cod_4 codes
        for i in range(1, 5):
            cod = f'cod_{i}'
            if row[cod]:
                codes.append(row[cod])
        
        # Append the collected codes to the main list
        cod_codes.append(codes)

# Write the collected COD codes to a text file
with open('cod_codes.txt', 'w') as outfile:
    for index, codes in enumerate(cod_codes):
        outfile.write(f"{codes}\n")

print("COD codes have been written to cod_codes.txt")