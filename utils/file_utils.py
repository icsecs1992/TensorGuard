import json

def load_json(data_path):
    with open(data_path) as json_file:
        data = json.load(json_file)
    return data