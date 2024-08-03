import sys
from bs4 import BeautifulSoup as soup
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
import re
from csv import writer
import pandas as pd
import ast
import subprocess
import json
import requests
import os
import time, csv
from pydriller import Repository
from collections import Counter
import numpy as np
ROOT_DIR = os.getcwd()

REG_CHANGED = re.compile(".*@@ -(\d+),(\d+) \+(\d+),(\d+) @@.*")
REG_LOC_FLAWFINDER = re.compile('\:(\d+)\:')
REG_RATS = re.compile('<vulnerability>')
REG_CPP_CHECK_LOC = re.compile('line=\"(\d+)\"')
REG_CPP_CHECK = re.compile('error id=')

FIND_CWE_IDENTIFIER = re.compile('CWE-(\d+)')
FIND_RATS_VUL_TYPE = re.compile('<type.*>((.|\n)*?)<\/type>')

def get_patches(splitted_lines):
    change_info = {}
    i = 0
    for line in splitted_lines:
        if REG_CHANGED.match(line):
            i += 1
            addStart = int(REG_CHANGED.search(line).group(1))
            addedLines = int(REG_CHANGED.search(line).group(2))
            deletedStart = int(REG_CHANGED.search(line).group(3))
            deletedLines = int(REG_CHANGED.search(line).group(4))
                        
            start = deletedStart
            if(start == 0):
                start += 1
    
            end = addStart+addedLines-1
            change_info[i] = [deletedStart, deletedStart+deletedLines]

    super_temp = []
    j = 0
    indices = []
    while j < len(splitted_lines):
        if re.findall(r'(@@)',splitted_lines[j]):
            indices.append(j)
        j += 1

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
            for row in range(indices[i]+1, indices[j]):
                temp.append(splitted_lines[row])
            super_temp.append(temp)
            if j == len(indices)-1:
                temp = [] 
                for row in range(indices[j]+1, len(splitted_lines)):
                    temp.append(splitted_lines[row])
                super_temp.append(temp)
                break
            i+= 1
            j+= 1
    return super_temp, change_info

def get_diff_header(diff):
    code_lines = diff.split('\n')
    [super_temp, change_info] = get_patches(code_lines)
    return change_info

def get_fix_file_names(commit):
    f_names = {}
    raw_name = []
    if 'test' not in commit.filename:
        diff_split = get_diff_header(commit.diff)
        if bool(commit.new_path):
            f_names[commit.new_path] = diff_split
            raw_name.append(commit.new_path)
        else:
            f_names[commit.old_path] = diff_split
            raw_name.append(commit.old_path)
    else:
        if 'test' not in commit.filename:
            diff_split = get_diff_header(commit.diff)
            if bool(commit.new_path):
                f_names[commit.new_path] = diff_split
                raw_name.append(commit.new_path)
            else:
                f_names[commit.old_path] = diff_split
                raw_name.append(commit.old_path)
    return f_names, raw_name

def changed_lines_to_list(cl):
    global_list = []
    for k, v in cl.items():
        for sk, sv in v.items():
            global_list = global_list + sv
    return global_list

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


def parse_sub_element(data):
    for elem in data.contents:
        if isinstance(elem, str):
            return elem
        else:
            return parse_sub_element(elem)


def recursive_parse_api_description(data):
    g = []
    for elem in data.contents:
        if isinstance(elem, str):
            g.append(elem)
        else:
            x = parse_sub_element(elem)
            g.append(x)
    return g


def search(data, target_api):
    try:
        for element in data:
            for key, value in element.items():
                if key == target_api:
                    return value
    except Exception as e:
        return 'Could not find your target API from the database!'


def recursive_parse_api_sequence(data):
    if isinstance(data.contents[0], str):
        return data.contents[0]
    for elem in data.contents:
        if not isinstance(elem, str):
            return recursive_parse_api_sequence(elem)


def format_code(code_):
    lines_decomposed = decompose_code_linens(code_)
    code = ''
    for line in lines_decomposed:
        line = "".join(line)
        code = code + line
    return code


def get_code_change(sha):
    changes = []
    changed_lines = []
    before_union = []
    after_union = []
    try:
        for commit in Repository('repos/tensorflow', single=sha).traverse_commits():
            for modification in commit.modified_files:
                cl, raw_name = get_fix_file_names(modification)
                cl_list = changed_lines_to_list(cl)
                changes.append(modification.diff)
                changed_lines.append(cl)
                before_union.append(modification.source_code_before.split('\n'))
                after_union.append(modification.source_code.split('\n'))
    except Exception as e:
        print(e)
    return changes, before_union,after_union, changed_lines


def calculate_rule_importance(data):
    element_frequency = Counter(data['Anomaly'].values.flatten())
    total_elements = len(data['Anomaly'].values.flatten())
    element_importance = {element: frequency /
                          total_elements for element, frequency in element_frequency.items()}
    return sorted(element_importance.items(), key=lambda x: x[1], reverse=True)


def read_txt(fname):
    with open(fname, 'r') as fileReader:
        data = fileReader.read().splitlines()
    return data

    # api_link = f"https://api.github.com/repos/tensorflow/tensorflow/commits/{sha}"


def scrape_security_page(link):
    code_flag = False
    change_flag = False

    sub_content = requests.get(link)
    page_soup_home = soup(sub_content.text, "html.parser")
    app_main_ = page_soup_home.contents[3].contents[3].contents[1].contents[9]

    title_ = app_main_.contents[1].contents[3].contents[1].contents[
        1].contents[1].contents[1].contents[1].contents[1].contents[0]

    main_elements = app_main_.contents[1].contents[3].contents[1].contents[1].contents[
        3].contents[1].contents[1].contents[1].contents[3].contents[3].contents[1].contents

    description_ = recursive_parse_api_description(main_elements[3])
    description_ = list(filter(lambda item: item is not None, description_))
    description_ = " ".join(description_)

    for j, item in enumerate(main_elements):
        if not isinstance(item, str):
            d_ = recursive_parse_api_description(item)
            d_ = list(filter(lambda x: x is not None, d_))
            matching_sentences = [
                sentence for sentence in d_ if 'patched' in sentence]
            if matching_sentences:
                if d_[-1] == '.':
                    code_changes, source_code_before, source_code_after, changed_lines = get_code_change(d_[1])
                    if code_changes:
                        change_flag = True
                    break

    for item in main_elements:
        if not isinstance(item, str):
            if 'class' in item.attrs and "highlight-source-python" in item.attrs['class']:
                code_ = recursive_parse_api_description(item.contents[0])
                code_formated = format_code(code_)
                code_flag = True
    
    union_buggy = []
    union_fix = []
    file_extensions = ['.h', '.cc', '.cpp', '.cu', '.py', '.hpp']

    if change_flag:
        for idx, mods in enumerate(changed_lines):
            for k, v in mods.items():
                for key,value in v.items():
                    if any(extension in k.split('/')[-1] for extension in file_extensions) :
                        union_buggy.append(source_code_before[idx-1][value[0]:value[1]])
                        union_fix.append(source_code_after[idx-1][value[0]:value[1]])

    if code_flag and change_flag:
        data = {'Title': title_,
                'Bug description': description_,
                'Sample Code': code_formated,
                'Code change': code_changes,
                'Buggy Code': union_buggy,
                'Clean Code': union_fix}
    elif code_flag == True and change_flag == False:
        data = {'Title': title_,
                'Bug description': description_,
                'Sample Code': code_formated}
    elif code_flag == False and change_flag == True:
        data = {'Title': title_,
                'Bug description': description_,
                'Sample Code': '',
                'Code change': code_changes,
                'Buggy Code': union_buggy,
                'Clean Code': union_fix
                }
    else:
        data = {'Title': title_,
                'Bug description': description_,
                'Sample Code': ''
                }

    return data, union_buggy, union_fix


def search_in_tuples(target_tuple, target_rule):
    for item in target_tuple:
        if item[0] == target_rule:
            return item[1]
        else:
            continue


def scrape_tensorflow_security_from_list(hash_table):
    data = pd.read_csv('data/TF_RECORDS.csv', encoding='utf-8', delimiter=',')
    weights_ = calculate_rule_importance(data)
    for idx, row in data.iterrows():
        print(row['API'])
        _target_api = search(hash_table, target_api=row['API'])
        full_link = row['Advisory Link']
        try:
            data_, buggy_snippets, fix_snippets = scrape_security_page(full_link)
            data_.update({'Link': full_link})
            data_.update({'API Signature': _target_api})

            score_ = search_in_tuples(weights_, row['Anomaly'])

            data_.update({'Score': score_})
            data_.update({'Anomaly': row['Anomaly']})
            data_.update({'Anomaly Description': row['Anomaly description']})
            data_.update({'Category': row['Category']})
            data_.update({'Argument': row['Reproducing Example']})

            with open("data/tf_bug_data_new.json", "a") as json_file:
                json.dump(data_, json_file, indent=4)
                json_file.write(',')
                json_file.write('\n')
        except Exception as e:
            print(e)


def scrape_tensorflow_security():

    data_list = []
    for page_num in range(1, 43):
        time.sleep(2)
        sub_content = requests.get(
            f"https://github.com/tensorflow/tensorflow/security/advisories?page={page_num}")
        page_soup2 = soup(sub_content.text, "html.parser")
        app_main_ = page_soup2.contents[3].contents[3].contents[1].contents[9]
        box_content = app_main_.contents[1].contents[3].contents[
            1].contents[3].contents[1].contents[3].contents[1].contents[5]
        records = box_content.contents[1].contents[1]

        for record in records.contents:
            if not isinstance(record, str):
                link_text = record.contents[1].contents[3].contents[1].contents
                partial_link = link_text[1].attrs['href']
                record_title = link_text[1].contents[0]

                full_link = f"https://github.com{partial_link}"
                print(full_link)
                data_ = scrape_security_page(full_link)
                data_[0].update({'Title': record_title})
                data_[0].update({'Link': full_link})

                # data_list.append(data_)
                list_data = [full_link, data_[0]['Title'], data_[0]['Bug description']]
                with open("./data/tf_validation_bug_data.csv","a", newline="\n",) as fd:
                    writer_object = csv.writer(fd)
                    writer_object.writerow(list_data)
   
    # with open("data/tf_bug_data.json", "a") as json_file:
    #     json.dump(data_list, json_file, indent=4)
    #     json_file.write('\n')


def ckeckList(lst):
    return len(set(lst)) == 1


def search_dict(d, q):
    if any([True for k, v in d.items() if v == q]):
        return True
    else:
        return False


def main():

    lib_name = 'tf'
    single_commit = True

    with open(f'API signatures/{lib_name}_API_table.json') as json_file:
        hash_table = json.load(json_file)

    if not os.path.exists('repos/tensorflow'):
        subprocess.call(
            f'git clone https://github.com/tensorflow/tensorflow.git repos/tensorflow', shell=True)

    # scrape_tensorflow_security_from_list(hash_table)
    scrape_tensorflow_security()


if __name__ == '__main__':
    main()
