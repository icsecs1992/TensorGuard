
import json, os, sys
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
client = OpenAI(
    api_key=os.environ.get(".env")
)

def completions_with_backoff(prompt, model='gpt-4o-mini'):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt}
        ]
    )
    return response


def root_cause_analysis_agent(commit_message):
    prompt_ = f"""
        Please describe the root cause of the bug based on the following commit message: {commit_message}
        Please do not explain how to fix the bug, your task is to just explain the root cause of the bug.
        <output>
        """
    response = completions_with_backoff(prompt_)
    return response.choices[0].message.content

def load_json(data_path):
    with open(data_path) as json_file:
        data = json.load(json_file)
    return data

def main(libname):
    counter = 0
    patch_counter = 0
    commit_counter = 0
    flag = False
    data = load_json(f"data/test data/filter2/{libname}_test_data.json")
    for j, item in enumerate(data):
        # print(f"Running record {j}/{len(data)}")
        if item['label'] == 'YES':
            # response = root_cause_analysis_agent(item['message'])
            for change in item['changes']:
                if change['patches']:
                    commit_counter = commit_counter + 1
                    print(f"Total Commits {commit_counter}")
                    for patch in change['patches']:
                        patch_counter = patch_counter + 1
                        print(f"Total Patches {patch_counter}")
            # if flag:
            #     counter = counter + 1
            #     print(counter)
                #     path = change['path']
                #     location = f"The location of bug is the following file: {path}"
                #     path_obj = Path(path)
                #     new_file_name = path_obj.stem + ".txt"
                #     with open(f"data/acr_data/{libname}/{j}_{item['commit_link'].split('/')[-1]}_{new_file_name}", "w") as file:
                #         file.write('response' + "\n")
                #         file.write(location + "\n")
                                        

if __name__ == '__main__':
    libname = 'tensorflow'
    main(libname)