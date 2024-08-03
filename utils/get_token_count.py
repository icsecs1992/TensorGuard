

import tiktoken


def get_token_count(string):

    encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")

    num_tokens = len(encoding.encode(string))

    return num_tokens


prompt = ''' Generate a python test case that use torch.rand() API. '''

print(get_token_count(prompt))
