
import json
from sklearn.model_selection import train_test_split

def loadJSONL(jsonl_file_path):
    with open(jsonl_file_path, 'r') as file:
        data = [json.loads(line) for line in file]
    return data

def split_(data):
    # Split the data into training, testing, and validation sets
    train_data, test_val_data = train_test_split(data, test_size=0.3, random_state=42)
    test_data, val_data = train_test_split(test_val_data, test_size=0.5, random_state=42)

    # Save the split datasets into separate JSONL files
    def save_to_jsonl(file_path, data):
        with open(file_path, 'w') as file:
            for entry in data:
                file.write(json.dumps(entry) + '\n')

    save_to_jsonl('finetune/train_data.jsonl', train_data)
    save_to_jsonl('finetune/test_data.jsonl', test_data)
    save_to_jsonl('finetune/val_data.jsonl', val_data)



if __name__ == '__main__':
    data = loadJSONL('data/train.jsonl')
    split_(data)