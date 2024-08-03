import pandas as pd
import os, re, json, random
INDEX_HOLDER = {}

def remove_comments_func(data):
    output = []
    for item in data:
        code = item['Deleted lines']
        split_code = code.split('\n')
        filtered_statements = [statement for statement in split_code if not statement.strip().startswith("#")]
        filtered_statements = [statement for statement in filtered_statements if not statement.strip().startswith("//")]
        item['Deleted lines'] = "\n".join(filtered_statements)
        output.append(item)
    return output

def select_specific_violations(data, violation_type):
    output = []
    for item in data:
        if item['Violation'] == violation_type:
            output.append(item)
    return output

def match_data(data):
    selected_output = []
    for key, val in INDEX_HOLDER.items():
        for item in data:
            if key == item['Id']:
                selected_output.append(item)
    return selected_output

def save_index(data):
    for item in data:
        INDEX_HOLDER[item['Id']] = item['Commit Link']

if __name__ == '__main__':
    store_index = True
    violation_type = 'improper'
    remove_comments = True
    
    for root, dirs, files in os.walk(r'data'):
        for file in files:
            if re.findall(r'(data\_)', file):
                with open(f'{root}/{file}') as json_file:
                    data = json.load(json_file)

                    if violation_type:
                        data = select_specific_violations(data, violation_type)
                    if remove_comments:
                        data = remove_comments_func(data)
                    if store_index:
                        random_data = random.sample(population=data, k=50)
                        save_index(random_data)
                    else:
                        random_data = match_data(data)
                    store_index = False
                    with open(f"data/subject_data/{file}", "w") as json_file:
                        json.dump(random_data, json_file, indent=4)
                        json_file.write(',')
                        json_file.write('\n')