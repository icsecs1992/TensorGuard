from pydriller import Repository
import re, os, sys, json, csv
import pandas as pd
import subprocess
from unidiff import PatchSet

ROOT_DIR = os.getcwd()
REG_CHANGED = re.compile(".*@@ -(\d+),(\d+) \+(\d+),(\d+) @@.*")
REG_LOC_FLAWFINDER = re.compile('\:(\d+)\:')
REG_RATS = re.compile('<vulnerability>')
REG_CPP_CHECK_LOC = re.compile('line=\"(\d+)\"')
REG_CPP_CHECK = re.compile('error id=')
FIND_CWE_IDENTIFIER = re.compile('CWE-(\d+)')
FIND_RATS_VUL_TYPE = re.compile('<type.*>((.|\n)*?)<\/type>')

def write_to_csv(data, agent_type):
    with open(f"output_{agent_type}.csv", 'a', encoding="utf-8", newline='\n') as file_writer:
        write = csv.writer(file_writer)
        write.writerow(data)
        
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

def get_patches(splitted_lines):
    change_info = {}
    i = 0
    for line in splitted_lines:
        if REG_CHANGED.match(line):
            i += 1
            deletedStart = int(REG_CHANGED.search(line).group(1))
            deletedLines = int(REG_CHANGED.search(line).group(2))
            addStart = int(REG_CHANGED.search(line).group(3))
            addedLines = int(REG_CHANGED.search(line).group(4))
                        
            start = deletedStart
            if(start == 0):
                start += 1
    
            end = addStart+addedLines-1
            change_info[i] = [deletedStart, deletedStart+deletedLines, addStart, addStart+addedLines]

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

def get_added_deleted_lines(mod):
    out = []
    for item in mod:
        out.append(item[1])
    return "\n".join(out)

def split_multiple_diffs(lines):
    diffs = []
    current_diff_block = []
    for line in lines:
        if line.startswith('@@'):
            if current_diff_block:
                diffs.append('\n'.join(current_diff_block))
                current_diff_block = []
        current_diff_block.append(line)
    if current_diff_block:
        diffs.append('\n'.join(current_diff_block))
    return diffs

def new_added_deleted_lines(lines, cl, source_code_before, source_code, context_window, use_context):
    split_lines = lines.split('\n')
    source_code_before = source_code_before.split('\n')
    source_code = source_code.split('\n')
    
    added_lines_mod = []
    deleted_lines_mod = []

    for line in split_lines:
        if line.startswith('+++') or line.startswith('---'):
            continue  
        if line.startswith('+'):
            added_lines_mod.append(line)
        elif line.startswith('-'):
            deleted_lines_mod.append(line)
        else:
            pass
    if use_context:
        if cl[0]-context_window < 0:
            before_hung = source_code_before[cl[1]:cl[1]+context_window]
            after_hung = source_code[cl[3]:cl[3]+context_window]
            
            added_lines_mod = added_lines_mod + after_hung
            deleted_lines_mod = deleted_lines_mod + before_hung
        else:
            deleted_hung_before = source_code_before[cl[0]-context_window:cl[0]]
            deleted_hung_after = source_code_before[cl[1]:cl[1]+context_window]
            added_hung_before = source_code[cl[2]-context_window-1:cl[2]]
            added_hung_after = source_code[cl[3]:cl[3]+context_window]
            
            added_lines_mod = added_hung_before + added_lines_mod + added_hung_after
            deleted_lines_mod = deleted_hung_before + deleted_lines_mod + deleted_hung_after

            
        deleted_lines_mod = list(filter(lambda x: x != '', deleted_lines_mod))
        added_lines_mod = list(filter(lambda x: x != '', added_lines_mod))
    return added_lines_mod, deleted_lines_mod
    

def get_code_change(sha, libname, context_window, use_context):
    changes = []
    changed_lines = []
    before_union = []
    after_union = []
    stat = []
    try:
        for commit in Repository(f'ml_repos/{libname}/{libname}', single=sha).traverse_commits():
            date_ = commit.author_date.strftime('%Y/%m/%d')
            for modification in commit.modified_files:
                if 'test' in modification.filename or 'tests' in modification.filename:
                    continue
                lines = modification.diff.splitlines()
                diffs = split_multiple_diffs(lines)
                #if file_name.split('/')[-1] == modification.filename:
                cl, raw_name = get_fix_file_names(modification)
                cl_list = changed_lines_to_list(cl)
                added_lines = []
                deleted_lines = []
                for i, diff in enumerate(diffs):
                    current_cl = cl[raw_name[0]][i+1]
                    added_, deleted_ = new_added_deleted_lines(diff, current_cl, modification.source_code_before, modification.source_code, context_window, use_context)
                    added_lines = added_lines + added_
                    deleted_lines = deleted_lines + deleted_
                    # added_lines = get_added_deleted_lines(modification.diff_parsed['added'])
                    # deleted_lines = get_added_deleted_lines(modification.diff_parsed['deleted'])
                changes.append(modification.diff)
                changed_lines.append(cl)
                before_union.append(modification.source_code_before.split('\n'))
                after_union.append(modification.source_code.split('\n'))
                stat.append([cl, modification.source_code_before, deleted_lines, modification.source_code, added_lines, date_, commit])
    except Exception as e:
        print(e)
    return stat

def slice_code_base(changed_lines, code_before, deleted_lines, code, added_lines, ctx_window):
    split_code_before = code_before.split('\n')
    split_code = code.split('\n')
    # if changed_lines[0][1][0]-ctx_window < len(split_code):
    #     lower_bound = changed_lines[0][1][0]
    #     upper_bound = changed_lines[0][1][1]+ctx_window
    # elif changed_lines[0][1][0]-ctx_window >  and
    for item in deleted_lines:
        split_code_before[item[0]] = '-' + split_code_before[item[0]]
    for item in added_lines:
        split_code[item[0]] = '+' + split_code[item[0]]
    split_code_before = split_code_before[changed_lines[0][1][0]-ctx_window:changed_lines[0][1][1]+ctx_window]
    split_code = split_code[changed_lines[0][1][0]-ctx_window:changed_lines[0][1][1]+ctx_window] 
    return ["\n".join(split_code_before), "\n".join(split_code)]

if __name__ == '__main__':

    # full_link = sys.argv[1]
    # file_name = sys.argv[2]

    out_buggy = {
        'code': [],
    }

    out_clean = {
        'code': []
    }

    data = pd.read_csv('mining/commits_new/pytorch/pytorch.csv')
    
    counter = 0
    context_window = 0
    line_of_code = 10
    use_context = False
    
    if use_context:
        fname = f"pytorch_json_data.json"
    else:
        fname = f"pytorch_json_data.json"
    for idx, row in data.iterrows():
        full_link = row['Commit'].split('/')[-1]

        if row['Library'] == 'tensorflow' or row['Library'] == 'pytorch':
            repository_path = ROOT_DIR+'/ml_repos/'+row['Library']
        else:
            repository_path = ROOT_DIR+'/ml_repos/'+row['Library']+'/'+dir.split('_')[1].split('.')[0]

        v = f"https://github.com/{row['Library']}/{row['Library']}.git"

        if not os.path.exists(repository_path):
            subprocess.call('git clone '+v+' '+repository_path, shell=True)
                
        commit_stat = get_code_change(full_link, row['Library'], context_window, use_context)
        if commit_stat:
            changed_lines = [commit_stat[0][0][key] for key in commit_stat[0][0]]
            if len(commit_stat[0][4]) < line_of_code:
                print(row['Commit'])
                counter = counter + 1
                    # code = slice_code_base(changed_lines, commit_stat[0][1], commit_stat[0][2], commit_stat[0][3], commit_stat[0][4], ctx_) 
                data_ = {
                        "Id": counter,
                        'Library': row['Library'],
                        'Date': commit_stat[-2],
                        'Commit Link': row['Commit'],
                        'Root Cause': row['Root Cause'],
                        'Bug report': row['bug report'],
                        "Number of deleted lines": len(commit_stat[0][2]),
                        "Deleted lines": "\n".join(commit_stat[0][2]),
                        "Added lines": "\n".join(commit_stat[0][4]),
                        'Label': row['Label']}
                    
                # write_to_csv([commit_stat[0][-1]], 'test')
                
                with open(f"data/{fname}", "a") as json_file:
                    json.dump(data_, json_file, indent=4)
                    json_file.write(',')
                    json_file.write('\n')
                    
            else:
                continue
            

  