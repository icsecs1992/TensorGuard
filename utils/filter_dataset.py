import pandas as pd
import subprocess, os
from pydriller import Repository
from datetime import datetime, timezone
import csv, json

ROOT_DIR = os.getcwd()

CHECKERS = ['TFLITE_CHECK(', 'TORCH_INTERNAL_ASSERT(', 'TORCH_CHECK(',
    'CHECK_GT(', 'CHECK_LE(', 'CHECK_LT(', 'OP_REQUIRES(', 'CHECK(',
    'C10_CUDA_CHECK(', 'check_tuple_output_sharding_condition(',
    'TF_LITE_KERNEL_LOG(', 'OP_REQUIRES_OK(', 'TF_LITE_ENSURE_OK(',
    'TF_RET_CHECK(', 'TORCH_INTERNAL_ASSERT_DEBUG_ONLY(', 'Expect(', 
    'TF_LITE_MAYBE_KERNEL_LOG(', 'TF_LITE_ENSURE_TYPES_EQ(','CHECK_GE(',
    'DCHECK(', 'TF_LITE_ENSURE_EQ(', 'DCHECK_LT(', 'TF_LITE_ENSURE(', 
    'ValidateInputTensors(', 'TFLITE_DCHECK_EQ(', 'TFLITE_DCHECK('
    'TORCH_CHECK_INDEX(', 'ExpectMaxOpVersion(', 'ExpectOpVersion(',
    'AT_ASSERT(', 'AT_CUDA_CHECK(', 'TF_RETURN_IF_ERROR(', 'TF_LITE_KERNEL_LOG(',
    'CAFFE_ENFORCE_LT(', 'CAFFE_ENFORCE_GT(', 'AT_ASSERTM(', 'CAFFE_ENFORCE_GE(',
    'TFLITE_DCHECK_GE(', 'ValidateFeedFetchCppNames(', 'TF_QCHECK_OK(',
    'CheckInputsCount(', 'CAFFE_NCCL_CHECK(', 'THCudaCheck(', 'CHECK_NE(',
    'if (', 'if ', 'isinstance(', 'assert ', 'tf.debugging.is_numeric_tensor(',
    'tensorflow::DataTypeIsNumeric(', 'kNumberTypes.Contains(','_type_utils.JitScalarType(',
    'AT_DISPATCH_ALL_TYPES', 'isTensor()', 'th_isnan(', 'is_variable(',
    'C10_CUDA_KERNEL_LAUNCH_CHECK(', 'array_ops.check_numerics(']

def contains_checker(hunk, hunk_added_deleted):
    deleted = hunk_added_deleted[0]
    added = hunk_added_deleted[1]
    check1 = any(checker in deleted for checker in CHECKERS)
    check2 = any(checker in added for checker in CHECKERS)
    if check1 or check2:
        return True
    else:
        return False 

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

def load_json(data_path):
    with open(data_path) as json_file:
        data = json.load(json_file)
    return data

def write_to_csv(data, agent_type):
    with open(f"output_{agent_type}.csv", 'a', encoding="utf-8", newline='\n') as file_writer:
        write = csv.writer(file_writer)
        write.writerow(data)

def exclude():
    pass

def check_commit_exists(all_data, a):
    df_filtered = all_data[~all_data['Commit'].isin(a)]
    return df_filtered

def is_after_september_2021(date):
    september_2021 = datetime(2021, 9, 30, tzinfo=timezone.utc)
    return date > september_2021

def extract_within_time_range(data, lib_name):
    start_date = '2024-01-01'
    end_date = '2024-07-20'
    start = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    j = 0
    for item in data:
        commit_info = {
            'commit_link': item['commit_link'],
            'message': item['message'],
            'date': item['date'],
            'label': item['label'],
            'changes': []
        }
        if start <= datetime.fromisoformat(item['date']) <= end:
            for change in item['changes']:
                if 'test' in change['path'] or 'tests' in change['path']:
                    continue
                patches = []
                for hunk in change['patches']:
                    deleted_lines, added_lines = separate_added_deleted(hunk['hunk'])
                    loc_changed = len(deleted_lines.split('\n')) + len(added_lines.split('\n'))
                    if loc_changed <=15 and contains_checker(hunk['hunk'], [deleted_lines, added_lines]):
                        j = j + 1
                        patch = {
                                'Id': j,
                                'hunk size': loc_changed,
                                'hunk': hunk['hunk']}

                        patches.append(patch)
                
                changed_file = {
                        'path': change['path'],
                        'patches': patches
                        }
                if changed_file: 
                    commit_info["changes"].append(changed_file)
        with open(f'data/test data/filter3/{lib_name}_test_data.json', 'a') as f:
                json.dump(commit_info, f, indent=4)
                f.write(',')
                f.write('\n')


def extract_non_biased(buggy_data, all_data):
    counter = 0
    new_buggy_data = []
    new_clean_data = []
    for idx, row in buggy_data.iterrows():
        full_link = row['Commit'].split('/')[-1]

        if row['Library'] == 'tensorflow' or row['Library'] == 'pytorch':
            repository_path = ROOT_DIR+'/ml_repos/'+row['Library']
        else:
            repository_path = ROOT_DIR+'/ml_repos/'+row['Library']+'/'+dir.split('_')[1].split('.')[0]

        v = f"https://github.com/{row['Library']}/{row['Library']}.git"

        if not os.path.exists(repository_path):
            subprocess.call('git clone '+v+' '+repository_path, shell=True)
        
        for commit in Repository(f"ml_repos/{row['Library']}", single=full_link).traverse_commits():
            if is_after_september_2021(commit.author_date):
                counter = counter + 1
                write_to_csv([row['Commit']], 'new_bug_data')
                new_buggy_data.append(row['Commit'])
                #a.append([row["Library"], row["Commit Link"], row["Root Cause"], row["Bug report"], "Number of deleted lines"], row["Deleted lines"], row["Added lines"])

    all_data = check_commit_exists(all_data, new_buggy_data)
    sampled_df = all_data.sample(n=len(new_buggy_data), random_state=42)
    sampled_df.to_csv('new_clean_data.csv', sep=',',index=False)
    

def main():
    lib_name = 'tensorflow'
    data = load_json(f"data/test data/filter1/{lib_name}_test_data.json")
    extract_within_time_range(data, lib_name)
    


if __name__ == '__main__':
    main()