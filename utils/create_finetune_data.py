import json
from sklearn.model_selection import train_test_split


DEFAULT_SYSTEM_PROMPT = 'You are an automatic program repair bot for fixing machine learning backend code. You should help to fix the buggy code.'

def create_dataset(buggy_code, clean_code):
    buggy_code_template = f"Here is a piece of buggy code: {buggy_code}"
    return {
        "messages": [
            {"role": "system", "content": DEFAULT_SYSTEM_PROMPT},
            {"role": "user", "content": buggy_code_template},
            {"role": "assistant", "content": clean_code},
        ]
    }

def loadJSON(_path_to_data):
    with open(_path_to_data, 'r') as file:
        # Load the JSON data from the file
        data = json.load(file)
    return data

def createDS(_path_to_data):
    data = loadJSON(_path_to_data)
    for row in data:
        row

if __name__ == '__main__':
    lib = "tf"
    _path_to_data = f"data/{lib}_bug_data.json"
    data = loadJSON(_path_to_data)
    with open("train.jsonl", "w") as f:
        for item in data:
            for idx, buggy_data in enumerate(item['Buggy Code']):
                sample_code = json.dumps(create_dataset("\n".join(buggy_data), "\n".join(item['Clean Code'][idx])))
                f.write(sample_code + "\n")