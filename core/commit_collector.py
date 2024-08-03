from csv import writer
import os, subprocess, re, csv
from git import Repo
from datetime import datetime
from datetime import datetime, timezone
from openai import OpenAI
import backoff, time
import openai, sys
import tiktoken
from dotenv import load_dotenv
load_dotenv()

client = OpenAI(
    api_key=os.environ.get(".env")
)

THIS_PROJECT = os.getcwd()

def write_list_to_txt4(data, filename):
    with open(filename, "a", encoding='utf-8') as file:
        file.write(data+'\n')
        
def no_matches_in_commit(commit_message, patterns):
    for pattern in patterns:
        if re.findall(pattern, commit_message):
            return True 
    return False


def save_commit(data, owner, libname):
    if not os.path.exists(f'mining/commits_new/{owner}/'):
        os.makedirs(f'mining/commits_new/{owner}/')

    with open(f"mining/commits_new/{owner}/{libname}.csv","a", newline="\n",) as fd:
        writer_object = csv.writer(fd)
        writer_object.writerow(data)

def read_txt(fname):
    with open(fname, "r") as fileReader:
        data = fileReader.read()
    return data

@backoff.on_exception(backoff.expo, openai.RateLimitError)
def completions_with_backoff(prompt, model='gpt-4-0125-preview'):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": prompt}
        ]
    )
    return response

def stage_1_prompting(item, libname):
    prompt_ = f"""
    You are a chatbot responsible for classifying a commit message that fixing bugs in {libname} backend implementation.
    Your task is to classify if the commit is fixing an improper/missing validation/checker bug. Please generate binary response, i.e., yes or no.

    Here is the commit message:
    Commit message: {item}

    Result: <your response>

    """

    return prompt_

def stage_2_prompting(item, libname):
    prompt_ = f"""
    You are a chatbot responsible for analyzing a commit message that fixing bugs in {libname} backend implementation.
    Your task is to perform analysis on the bug fixing commit that fixing an improper/missing validation/checker bug.

    Here is the commit message:
    Commit message: {item}
    
    Your analysis should contain the following factors:

    Root cause: <What is the root cause of the bug>
    Impact of the bug: <what is the impact of the bug>
    Fixing pattern: <how the bug is fixed>

    Please generate a short response for each factor. 
    Result: <your response>

    """

    return prompt_

def get_token_count(string):

    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")

    num_tokens = len(encoding.encode(string))

    return num_tokens

def main(owner, repo_name):
    # owner = 'google'
    # repo_name = 'jax'
    REPO_LIST = [f"https://github.com/{owner}/{repo_name}"]
    r_prime = REPO_LIST[0].split("/")

    v = REPO_LIST[0] + ".git"

    if not os.path.exists(
        THIS_PROJECT + "/ml_repos/" + r_prime[3] + "/" + r_prime[4]
    ):
        subprocess.call(
            "git clone "
            + v
            + " "
            + THIS_PROJECT
            + "/ml_repos/"
            + r_prime[3]
            + "/"
            + r_prime[4],
            shell=True,
        )

    r = Repo(THIS_PROJECT + "/ml_repos/" + r_prime[3] + "/" + r_prime[4])

    # subprocess.check_call(
    #     "./mining/checkout.sh %s "
    #     % (THIS_PROJECT + "/ml_repos_cloned/" + r_prime[3] + "/" + r_prime[4]),
    #     shell=True,
    # )

    subprocess.run("./mining/checkout.sh", shell=True)

    hisotry_file = f'logs/{r_prime[3]}_parsed_commits.txt'

    if not os.path.exists(hisotry_file):
        f1 = open(hisotry_file, 'a')

    if r_prime[3] == 'pytorch':
        max_count = 69389
        branch_name = 'main'
    elif r_prime[3] == 'google':
        max_count = 22127
        branch_name = 'main'
    else:
        max_count = 159725
        branch_name = "master"

    all_commits = list(r.iter_commits(branch_name, max_count=max_count))
    hist = read_txt(f'logs/{r_prime[3]}_parsed_commits.txt')

    rule_checks_initial = r"(\bchecker\b|\bvalidating\b|\bcheckers\b|\bchecking\b|\bparameter validation\b|\bvalidation vulnerability\b|\bboundary\b|\bboundary validation\b|\binvalid input\b|\bvalidation bypass\b|\bchecks\b|\bcheck\b|\bdata validation\b|\binput validation\b|\bvalidation\b|\bcheck\b)"
    rule_checks_l1 = r"(\bnumeric check\b|\bbackend check\b|\btype checkers\b|\bcheck if\b|\badd a check\b|\bdevice check\b|\bchecks of device type\b|\bin this check\b|\bexisting check\b|\bside effect checks\b|\bRelax the check\b|\bbefore checking\b|\bbut the check\b|\bto check\b|\badding a condition\b|\badding a condition to check\b|\bcheck that\b|\btypes checks\b|\bcheck bounds\b|\badd proper checks\b|\bsupports checks\b|\bRemove checks\b|\bAdd an extra level of checks\b|\bextra level of checks\b|\badd check\b|\bcheck to ensure\b|\bwithin valid range\b|\bworth checking\b|\bwe need to check\b|\blayering checks\b|\bchecks to fix\b|\bAdded size check\b|\bsize check\b|\bversion check\b|\badd checks\b|\badds more checks\b|\bcheck in\b|\badd additional checks\b|\badd additional checks for valid\b|\bstill checks\b|\bimprove type checking\b|\bcheck the existence of\b)"
    rule_checks_l2 = r"(\bcheck for reductions\b|\bwe don't need to check\b|\bWhen checking\b|\bhandle the case\b|\bchecking if\b|\bdevice check\b|\bChecking for the attribute\b|\bchecking for\b|\bWe want to check that\b|\bVersionCheck\b|\bget rid of a check\b|\bmulti-GPU fusion check\b|\bWe have a function to check\b|\bvalue check\b|\bmore checks\b|\bcheck only\b|\bconditional check\b|\bdon't check\b|\btype check\b|\bnull check\b|\bpadding check\b|\bAPI check\b|\bmemory kind check\b|\bExplicitly check\b|\bthe checks that check\b|\bwithin range\b|\bcheck to check\b|\bfunction check\b|\bcheck if\b|\blegality check\b|\bwe check\b|\bsafety check\b|\bdisabled checks\b|\bcheck the last element\b|\blater check\b|\bplatform check\b|\bduplicate checks\b|\bFix check\b|\bAdd validation to check\b)"
    rule_checks_l3 = r"(\bcheck error\b|\bValidate null\b|\binitial checks\b|\bcheck failure\b|\bcheck failed\b|\bedge cases\b|\bedge case\b|\bcheck for out of range\b|\bcheck for float\b|\bSkip checking\b|\brank checking\b)"
    
    try:
        temp = []
        for i, com in enumerate(all_commits):
            com.diff
            if com.hexsha not in hist:
                write_list_to_txt4(com.hexsha, f'logs/{r_prime[3]}_parsed_commits.txt')
                _date = datetime.fromtimestamp(com.committed_date)

                _match1 = re.findall(rule_checks_initial, com.message)
                _match2 = re.findall(rule_checks_l1, com.message)
                _match3 = re.findall(rule_checks_l2, com.message)
                _match4 = re.findall(rule_checks_l3, com.message)
                patterns = [rule_checks_initial, rule_checks_l1, rule_checks_l2, rule_checks_l3]
                print("Analyzed commits: {}/{}".format(i, len(all_commits)))

                parent = com.parents[0]

                diffs  = {
                    diff.a_path: diff for diff in com.diff(parent)
                }
                # if len(diffs) == 1:
                file_name = list(diffs.keys())
                if len(file_name) == 1:
                    if 'test' in file_name or 'tests' in file_name:
                        print('this change is related to tests, so I am ignoring it.')
                        continue
                        # if no_matches_in_commit(com.message, patterns):
                if _match1 or _match2 or _match3 or _match4:
                                # prompt_ = stage_2_prompting(com.message, r_prime[3])
                                # t_count = get_token_count(prompt_)
                                # if t_count <= 4097:
                                #     time.sleep(3)
                                #     conversations = completions_with_backoff(prompt_)
                                #     decision = conversations.choices[0].message.content
                                #     decision_split = decision.split('\n')
                                #     filtered_list = list(filter(None, decision_split))

                    commit_link = REPO_LIST[0] + "/commit/" + com.hexsha
                    commit_date = com.committed_date
                    dt_object = datetime.fromtimestamp(commit_date)
                    commit_date = dt_object.replace(tzinfo=timezone.utc)
                    # print(commit_date.year)
                    if commit_date.year > 2023:
                        data = [commit_link, commit_date.strftime("%Y-%m-%d")]
                        save_commit(data, owner, repo_name)
            else:
                print('This commit has been already analyzed!')

    except Exception as e:
        print(e)

if __name__ == "__main__":
    owner = sys.argv[1]
    repo_name = sys.argv[2]
    # library_name = 'pytorch'
    main(owner, repo_name)