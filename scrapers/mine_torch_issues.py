import json
import re
import os
import re
import subprocess
import requests
import random
import datetime
import time
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import pandas as pd
from csv import writer
from pydriller import Repository
from collections import Counter
from dotenv import load_dotenv
load_dotenv()

tokens = {0: os.getenv("GIT_TOKEN0"), 1: os.getenv("GIT_TOKEN1"),
          2: os.getenv("GIT_TOKEN2"), 3: os.getenv("GIT_TOKEN3")}

tokens_status = {os.getenv("GIT_TOKEN0"): True, os.getenv("GIT_TOKEN1"): True,
                 os.getenv("GIT_TOKEN2"): True, os.getenv("GIT_TOKEN3"): True}


def search(data, target_api):
    try:
        for element in data:
            for key, value in element.items():
                key = key.replace('\n', '')
                key = key.replace(' ', '')
                if key == target_api:
                    return value
    except Exception as e:
        return 'Could not find your target API from the database!'


def decompose_code_linens(splitted_lines):
    super_temp = []
    j = 0
    indices = []
    while j < len(splitted_lines):
        if '\n' in splitted_lines[j]:
            indices.append(j)
        j += 1

    if bool(indices) == False:
        return splitted_lines

    if len(indices) == 1:
        for i, item in enumerate(splitted_lines):
            if i != 0:
                super_temp.append(item)
        super_temp = [super_temp]
    else:
        i = 0
        j = 1
        while True:
            temp = []
            for row in range(indices[i], indices[j]):
                temp.append(splitted_lines[row+1])
            super_temp.append(temp)
            if j == len(indices)-1:
                temp = []
                for row in range(indices[j], len(splitted_lines)):
                    temp.append(splitted_lines[row])
                super_temp.append(temp)
                break
            i += 1
            j += 1

    return super_temp


def read_txt(fname):
    with open(fname, 'r') as fileReader:
        data = fileReader.read().splitlines()
    return data


def requests_retry_session(
    retries=3,
    backoff_factor=0.3,
    status_forcelist=(500, 502, 504),
    session=None,
):
    session = session or requests.Session()
    retry = Retry(
        total=retries,
        read=retries,
        connect=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    return session


retries = 10
now = datetime.datetime.now()


def search_comit_data(c, commit_data):
    t = []

    for item in commit_data:
        temp = item.split('/')
        t.append('/' + temp[3] + '/' + temp[4] + '/')

    r_prime = c.split('/')
    x = '/' + r_prime[3] + '/' + r_prime[4] + '/'
    if any(x in s for s in t):
        return True
    else:
        return False


def calculate_rule_importance(data):
    element_frequency = Counter(data['Anomaly'].values.flatten())
    total_elements = len(data['Anomaly'].values.flatten())
    element_importance = {element: frequency /
                          total_elements for element, frequency in element_frequency.items()}
    return sorted(element_importance.items(), key=lambda x: x[1], reverse=True)


def search_in_tuples(target_tuple, target_rule):
    for item in target_tuple:
        if item[0] == target_rule:
            return item[1]
        else:
            continue


def select_access_token(current_token):
    x = ''
    if all(value == False for value in tokens_status.values()):
        for k, v in tokens_status.items():
            tokens_status[k] = True

    for k, v in tokens.items():
        if tokens_status[v] != False:
            x = v
            break
    current_token = x
    return current_token


def miner(hash_table):

    current_token = tokens[0]
    # torch_issues = read_txt('data/torch_issues.txt')

    torch_issues = pd.read_csv(
        'data/TORCH_RECORDS.csv', sep=',', encoding='utf-8')

    issue_flag = False

    data_list = []
    weights_ = calculate_rule_importance(torch_issues)

    for idx, item in torch_issues.iterrows():
        print(item['Advisory Link'])
        sha_str = item['Advisory Link'].split('/')[-1]
        score_ = search_in_tuples(weights_, item['Anomaly'])
        _anomaly = item['Anomaly']
        _cat = item['Category']
        if 'commit' in item['Advisory Link']:
            commit_base_str = "https://api.github.com/repos/pytorch/pytorch"
            branchLink = f"{commit_base_str}/commits/{sha_str}"
        if 'issue' in item['Advisory Link']:
            issue_base_str = "https://api.github.com/repos/pytorch/pytorch"
            branchLink = f"{issue_base_str}/issues/{sha_str}"
            issue_flag = True

        response = requests_retry_session().get(
            branchLink, headers={'Authorization': 'token {}'.format(current_token)})

        if response.status_code != 200:
            tokens_status[current_token] = False
            current_token = select_access_token(current_token)
            response = requests_retry_session().get(
                branchLink, headers={'Authorization': 'token {}'.format(current_token)})

        if response.status_code != 200:
            tokens_status[current_token] = False
            current_token = select_access_token(current_token)
            response = requests_retry_session().get(
                branchLink, headers={'Authorization': 'token {}'.format(current_token)})

        if response.status_code != 200:
            tokens_status[current_token] = False
            current_token = select_access_token(current_token)
            response = requests_retry_session().get(
                branchLink, headers={'Authorization': 'token {}'.format(current_token)})

        if response.status_code != 200:
            tokens_status[current_token] = False
            current_token = select_access_token(current_token)
            response = requests_retry_session().get(
                branchLink, headers={'Authorization': 'token {}'.format(current_token)})

        data_ = json.loads(response.text)

        if issue_flag:
            issue_title_ = data_['title']

            issue_title_ = ""
            issue_description = ""
            issue_code = ""
            target_api = ""
            
            if re.findall(r'Summary((.|\n)*?)Segmentation fault in the CPU 2D kernel', data_['body']):
                issue_description = re.findall(
                    r'Summary((.|\n)*?)Segmentation fault in the CPU 2D kernel', data_['body'])[0][0]

            if re.findall(r'Bug((.|\n)*?)To Reproduce', data_['body']):
                issue_description = re.findall(
                    r'Bug((.|\n)*?)To Reproduce', data_['body'])[0][0]

            if re.findall(r'Describe the bug((.|\n)*?)code', data_['body']):
                issue_description = re.findall(
                    r'Describe the bug((.|\n)*?)code', data_['body'])[0][0]

            if re.findall(r'Describe the bug((.|\n)*?)Code example', data_['body']):
                issue_description = re.findall(
                    r'Describe the bug((.|\n)*?)Code example', data_['body'])[0][0]

            if re.findall(r'Problem((.|\n)*?)torch 1.11 and before', data_['body']):
                issue_description = re.findall(
                    r'Problem((.|\n)*?)torch 1.11 and before', data_['body'])[0][0]

            if re.findall(r'Describe the bug((.|\n)*?)Which results in:', data_['body']):
                issue_description = re.findall(
                    r'Describe the bug((.|\n)*?)Which results in:', data_['body'])[0][0]

            if re.findall(r'Describe the bug((.|\n)*?)Minimal example', data_['body']):
                issue_description = re.findall(
                    r'Describe the bug((.|\n)*?)Minimal example', data_['body'])[0][0]

            if re.findall(r'Bug((.|\n)*?)To clarify, the issue occurs when I do:', data_['body']):
                issue_description = re.findall(
                    r'Bug((.|\n)*?)To clarify, the issue occurs when I do:', data_['body'])[0][0]

            if re.findall(r'Bug((.|\n)*?)Expected behavior', data_['body']):
                issue_description = re.findall(
                    r'Bug((.|\n)*?)Expected behavior', data_['body'])[0][0]

            if re.findall(r'Describe the bug((.|\n)*?)Example to reproduce', data_['body']):
                issue_description = re.findall(
                    r'Describe the bug((.|\n)*?)Example to reproduce', data_['body'])[0][0]

            if re.findall(r'Describe the bug((.|\n)*?)To Reproduce', data_['body']):
                issue_description = re.findall(r'Describe the bug((.|\n)*?)To Reproduce',
                                               data_['body'])[0][0]

            if re.findall(r'description((.|\n)*)', data_['body']):
                issue_description = re.findall(
                    r'description((.|\n)*)', data_['body'])[0][0]

            if re.findall(r'Segmentation fault in the CPU 2D kernel((.|\n)*?)The CUDA kernels \(both 2D and 3D\)', data_['body']):
                issue_code = re.findall(
                    r'Segmentation fault in the CPU 2D kernel((.|\n)*?)The CUDA kernels \(both 2D and 3D\)', data_['body'])[0][0]

            if re.findall(r'To Reproduce((.|\n)*?)Environment', data_['body']):
                issue_code = re.findall(
                    r'To Reproduce((.|\n)*?)Environment', data_['body'])[0][0]

            if re.findall(r'To Reproduce((.|\n)*?)stdout:', data_['body']):
                issue_code = re.findall(
                    r'To Reproduce((.|\n)*?)stdout:', data_['body'])[0][0]

            if re.findall(r'To Reproduce((.|\n)*?)Expected behavior', data_['body']):
                issue_code = re.findall(
                    r'To Reproduce((.|\n)*?)Expected behavior', data_['body'])[0][0]

            if re.findall(r'Example to reproduce((.|\n)*?)Result', data_['body']):
                issue_code = re.findall(
                    r'Example to reproduce((.|\n)*?)Result', data_['body'])[0][0]

            if re.findall(r'To Reproduce((.|\n)*?)Output', data_['body']):
                issue_code = re.findall(
                    r'To Reproduce((.|\n)*?)Output', data_['body'])[0][0]

            if re.findall(r'To Reproduce((.|\n)*?)Error:', data_['body']):
                issue_code = re.findall(
                    r'To Reproduce((.|\n)*?)Error:', data_['body'])[0][0]

            if re.findall(r'torch 1.11 and before((.|\n)*?)torch 1.12:', data_['body']):
                issue_code = re.findall(
                    r'torch 1.11 and before((.|\n)*?)torch 1.12:', data_['body'])[0][0]

            if re.findall(r'Minimal example((.|\n)*?)leads to the following CLI output under torch 1.11.0, tested on two different systems:', data_['body']):
                issue_code = re.findall(
                    r'Minimal example((.|\n)*?)leads to the following CLI output under torch 1.11.0, tested on two different systems:', data_['body'])[0][0]

            if re.findall(r'Describe the bug((.|\n)*?)Versions', data_['body']):
                issue_code = re.findall(
                    r'Describe the bug((.|\n)*?)Versions', data_['body'])[0][0]

            if re.findall(r'Code((.|\n)*?)output', data_['body']):
                issue_code = re.findall(
                    r'Code((.|\n)*?)output', data_['body'])[0][0]

            if re.findall(r'Code example((.|\n)*?)By using this script,', data_['body']):
                issue_code = re.findall(
                    r'Code example((.|\n)*?)By using this script,', data_['body'])[0][0]

            if re.findall(r'To clarify, the issue occurs when I do:((.|\n)*?)but not for', data_['body']):
                issue_code = re.findall(
                    r'To clarify, the issue occurs when I do:((.|\n)*?)but not for', data_['body'])[0][0]

            if re.findall(r'To Reproduce((.|\n)*?)Additional context', data_['body']):
                issue_code = re.findall(
                    r'To Reproduce((.|\n)*?)Additional context', data_['body'])[0][0]

            target_api = search(hash_table, target_api=item['API'])

            data_ = {'Issue link': branchLink,
                         'Issue title': issue_title_,
                         'Bug description': issue_description,
                         'Sample Code': issue_code,
                         'API Signature': target_api,
                         'Bug fix': '',
                         'Score': score_,
                         'Category': _cat}

            issue_flag = False

        else:
            if not os.path.exists('repos/pytorch'):
                subprocess.call(
                    f'git clone https://github.com/pytorch/pytorch.git repos/pytorch', shell=True)

            changes = []
            try:
                for commit in Repository('repos/pytorch', single=sha_str).traverse_commits():
                    for modification in commit.modified_files:
                        changes.append(modification.diff)
            except Exception as e:
                print(e)

            target_api = search(hash_table, target_api=item['API'])

            data_ = {'Commit link': branchLink,
                     'Bug description': commit.msg,
                     'Sample Code': '',
                     'API Signature': target_api,
                     'Bug fix': changes,
                     'Score': score_,
                     'Anomaly': _anomaly,
                     'Categoery': _cat
                     }

        data_list.append(data_)

    with open("data/torch_bug_data.json", "a") as json_file:
        json.dump(data_list, json_file, indent=4)
        json_file.write('\n')


if __name__ == "__main__":
    lib_name = 'torch'
    with open(f'API signatures/{lib_name}_API_table.json') as json_file:
        api_hash_table = json.load(json_file)

    data = miner(api_hash_table)
