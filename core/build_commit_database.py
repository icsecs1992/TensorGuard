import git
import os, sys
import json
from unidiff import PatchSet
import pandas as pd
from pydriller import Repository
import pandas as pd
from collections import Counter
import os, re, json, tiktoken, backoff, csv
from openai import OpenAI
from dotenv import load_dotenv
import time, random
from sklearn.model_selection import train_test_split

load_dotenv()
client = OpenAI(
    api_key=os.environ.get(".env")
)
issue_pattern = re.compile(r'(Fixes|Closes) #(\d+)')

def separate_added_deleted(github_diff):
    diff_lines = github_diff.split('\n')

    added_lines = ""
    deleted_lines = ""

    for line in diff_lines:
        if line.startswith('+'):
            added_lines += line[0:] + '\n'
        elif line.startswith('-'):
            deleted_lines += line[0:] + '\n'
    return deleted_lines, added_lines

def write_to_csv(data, libname, mode):
    with open(f"{libname}_{mode}_statistics.csv", 'a', encoding="utf-8", newline='\n') as file_writer:
        write = csv.writer(file_writer)
        write.writerow(data)
        
def is_buggy(input_string):
    yes_variants = {"YES", "yes", "Yes"}
    return input_string in yes_variants

def bug_detection_agent(commit_message):
    prompt_ = f"""
        You are an AI trained to detect bugs in deep learning library backend code-base based on commit messages. 
        Given a commit message, detect if it is bug or not. Please generate YES or NO.
        
        Commit message: {commit_message}
        <output>
        """
    response = completions_with_backoff(prompt_)
    return response.choices[0].message.content

# @backoff.on_exception(backoff.expo, openai.error.RateLimitError)
def completions_with_backoff(prompt, model='gpt-4-turbo'):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt}
        ]
    )
    return response

def extract_related_issues(repo_path, commit_hash,lib_owner, libname, idx, row):
    repo = git.Repo(repo_path)
    try:
        commit = repo.commit(commit_hash)
        issues = issue_pattern.findall(commit.message)
        if issues:
            print(f"Commit {commit.hexsha}:")
    except Exception as e:
        print(e)
    
def is_valid_file_type(file_path):
    valid_extensions = ('.txt', '.ipynb', '.md')
    return file_path.endswith(valid_extensions)

def get_commit_with_changes(repo_path, commit_hash,lib_owner, libname, idx, row):
    repo = git.Repo(repo_path)
    commit = repo.commit(commit_hash)
    parent_commit = commit.parents[0] if commit.parents else None
    # time.sleep(2)
    # response = bug_detection_agent(commit.message.strip())
    
    output_list = [libname, f"https://github.com/{lib_owner}/{libname}/commit/{commit_hash}"]
    
    if 'Label' in row:
        commit_info = {
                "Id": idx, 
                "commit_link": f"https://github.com/{lib_owner}/{libname}/commit/{commit_hash}", 
                "date": commit.committed_datetime.isoformat(),
                "message": commit.message.strip(),
                "label": row['Label'],
                "changes": []
            }
    else:
        commit_info = {
                "Id": idx, 
                "commit_link": f"https://github.com/{lib_owner}/{libname}/commit/{commit_hash}", 
                "date": commit.committed_datetime.isoformat(),
                "message": commit.message.strip(),
                "changes": []
            }


    if parent_commit:
        diff = repo.git.diff(parent_commit, commit, ignore_blank_lines=True, ignore_space_at_eol=True)
        patch_set = PatchSet(diff)
        if len(patch_set.modified_files) < 10:
            output_list.append(len(patch_set.modified_files))
            num_hunks = 0
            total_loc = 0

            for patched_file in patch_set:
                file_path = patched_file.path
                if is_valid_file_type(file_path):
                    continue 
                
                file_name = os.path.basename(file_path)

                    # if 'test' in file_name or 'tests' in file_name:
                    #     continue            
                    
                patches = []
                whole_deleted = ""
                whole_added = ""
                whole_deleted_added = ""  
                for hunk in patched_file:
                    num_hunks = num_hunks + 1
                    loc_changed = hunk.added + hunk.removed
                    total_loc = total_loc + loc_changed
                    deleted_lines, added_lines = separate_added_deleted(str(hunk))
                    # if loc_changed <= 10:
                    patch = {
                                "old_start": hunk.source_start,
                                "old_length": hunk.source_length,
                                "new_start": hunk.target_start,
                                "new_length": hunk.target_length,
                                "hunk": str(hunk)
                            }
                    whole_deleted = whole_deleted + deleted_lines
                    whole_deleted_added = whole_deleted_added + str(hunk)
                    whole_added = whole_added + added_lines
                    patches.append(patch)
                            


                if patches:
                    file_change = {
                        "name": file_name,
                        "path": file_path,
                        "patches": patches,
                        "whole_deleted": whole_deleted,
                        "whole_added": whole_added,
                        "whole_hunk":  whole_deleted_added}
                    commit_info["changes"].append(file_change)

            output_list.append(num_hunks)
            output_list.append(total_loc)
            if 'Label' in row:
                output_list.append(row['Label'])

    return commit_info, output_list

def count_changes(changes):
    total_patches = 0
    for item in changes:
        total_patches = total_patches + len(item['patches'])
    return total_patches


def main(lib_owner, lib_name, task):
    repo_path = f"ml_repos/{lib_owner.lower()}/{lib_name.lower()}"
    
    if task == 'rag':
        data = pd.read_csv(f'mining/commits_{task}/{lib_owner}/{lib_name}.csv')
    else:
        data = pd.read_csv(f'mining/commits_{task}/{lib_owner}/{lib_name}.csv')
    # train_df, test_df = train_test_split(data, test_size=0.3, random_state=42)
    data_dict = {
        'train_data': data
        # 'test_data': test_df
    }

    total_modified_files = 0
    total_changes = 0
    
    if task == 'rag':
        if not os.path.exists(f'data/rag_data'):
            os.makedirs('data/rag_data')
        f = open(f'data/rag_data/{lib_name}_rag_data.json', 'a')
        f.write('[')
    if task == 'test':
        if not os.path.exists(f'data/test_data'):
            os.makedirs('data/test_data')
        f = open(f'data/test_data/{lib_name}_test_data.json', 'a')
        f.write('[') 
    for k, v in data_dict.items():
        for idx, row in v.iterrows():
            commit_hash = row.iloc[0].split('/')[-1]
            print(f"Processed {commit_hash}::{idx}/{len(v)}")
            # extract_related_issues(repo_path, commit_hash, lib_owner,lib_name, idx, row)
            commit_data, output_list = get_commit_with_changes(repo_path, commit_hash, lib_owner,lib_name, idx, row)
            total_modified_files = total_modified_files + len(commit_data['changes'])
            total_changes = total_changes + count_changes(commit_data['changes'])
            with open(f"data/{task}_data/metadata_{lib_name}.txt", "w") as file:
                file.write(f"Total number of changes:{total_modified_files}" + "\n")
                file.write(f"Total number of hunks:{total_changes}" + "\n")
                            
            if commit_data['changes']:
                # write_to_csv(output_list , lib_name, k)
                json.dump(commit_data, f, indent=4)
                if idx == len(v)-1:
                    break
                f.write(',')
                f.write('\n')
        f.write(']')
                    

if __name__ == '__main__':
    lib_owner = sys.argv[1]
    lib_name = sys.argv[2]
    task = sys.argv[3]
    main(lib_owner, lib_name, task)
    