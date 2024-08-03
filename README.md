## TensorGuard
This is the open-source repository of the paper titled **Taming Checker Bugs in Deep Learning Libraries** Submitted
to the International Conference on Software Engineering (ICSE) 2025 second cycle. 

:wave: We have taken extensive measures to ensure that this GitHub repository remains anonymous. We are also constantly updating the repository to improve the reproducibility of the package for other researchers.

<img src="https://github.com/icsecs1992/TensorGuard/blob/master/assets/ML_APR_flow_new.png" width="600" class="center">

### :wave: Overview
TensorGuard is an LLM-based automatic tool designed to detect and fix checker bugs in deep learning libraries.
It operates as a multi-agent tool and is equipped with a RAG vector database.
TensorGuard performs bug detection and program repair at the repository level, focusing on changes such as deleted and added lines in commits.

:bell: Currently, TensorGuard does not support a docker environment, so we recommend running it under virtual environments, e.g., Conda.

### Data
You can access all of our data as follows:

#### Keywords for filtering checker bugs
[Keywords](https://github.com/icsecs1992/TensorGuard/blob/master/assets/all_keywords.csv)<br>

#### Taxonomy of Checker Bugs
[Taxonomy data](https://github.com/icsecs1992/TensorGuard/blob/master/assets/taxonomyData.csv)<br>


| Library | Commits used for Taxonomy Creation | Evaluation Data | RAG Data |
|----------|----------|----------|----------|
| PyTorch | [PyTorch commits](https://github.com/icsecs1992/TensorGuard/blob/master/mining/commits/pytorch/pytorch.csv) | [PyTorch test data](https://github.com/icsecs1992/TensorGuard/blob/master/data/test%20data/filter2/pytorch_test_data.json) | [PyTorch commits](https://github.com/icsecs1992/TensorGuard/blob/master/mining/commits_rag/pytorch/pytorch.csv) |
| TensorFlow | [TensorFlow commits](https://github.com/icsecs1992/TensorGuard/blob/master/mining/commits/tensorflow/tensorflow.csv) | [TensorFlow test data](https://github.com/icsecs1992/TensorGuard/blob/master/data/test%20data/filter2/tensorflow_test_data.json) | [TensorFlow commits](https://github.com/icsecs1992/TensorGuard/blob/master/mining/commits_rag/tensorflow/tensorflow.csv) |


### :hammer: Setup & Running

First, create and activate an anaconda virtual environment:

```
conda create --name ENV_NAME python=3.9
conda activate ENV_NAME
```
:bell: We recommend using pyton3.9 as the default version of your Python interpreter.

Then you have to install the required packages:

```
conda install --file environment.json
```

After that, clone TensorGuard's repository and then cd to its directory:

```
https://github.com/icsecs1992/TensorGuard.git
cd TensorGuard
```

The first step is to set your OPENAI key:

```
export OPENAI_KEY=YOUR API KEY
```
Once you set your API key, you are ready to run TensorGuard. Please follow the guidelines in the next section

### :rocket: Getting started

The core components of TensorGuard are under ```core``` directory. 

There are six command-line arguments that you need to set before running TensorGuard:
- Target library name
- The level of granularity, e.g. running TensorGuard on code changes
- Prompting strategy
- Type of the task
- Model type

#### Before you run TensorGuard, you have to build the vector database for RAG

To build the vector, you need to build the dataset that is going to be used to build the vector database. 

Build dataset for PyTorch:

```
python core/build_commit_database.py pytorch pytorch rag 
```

Build dataset for TensorFlow:

```
python core/build_commit_database.py tensorflow tensorflow rag 
```

These commands will create datasets that are going to be used to build the RAG database. 

To build the RAG database for PyTorch:
```
python core/build_RAG_database.py pytorch 
```
To build the RAG database for TensorFlow:
```
python core/build_RAG_database.py tensorflow
```
By running these commands, you are ready to run TensorGuard.

#### Run TensorGuard on PyTorch library with 5 iterations using Zero-Shot scenario via GPT-3.5 Turbo model (Detection and Patch Generation):

```
python core/TensorGuard.py pytorch 5 patch_level zero generation gpt-3.5-turbo
```

#### Run TensorGuard on PyTorch library with 5 iterations using Few-Shot scenario via GPT-3.5 Turbo model (Detection and Patch Generation):

```
python core/TensorGuard.py pytorch 5 patch_level few generation gpt-3.5-turbo
```

#### Run TensorGuard on PyTorch library with 5 iterations using Chain of Thought scenario via GPT-3.5 Turbo model (Detection and Patch Generation):

```
python core/TensorGuard.py pytorch 5 patch_level cot generation gpt-3.5-turbo
```

:bell: If you only want the detection mode, you have to change the task type. 


#### Run TensorGuard on PyTorch library with 5 iterations using Chain of Thought scenario via GPT-3.5 Turbo model (Detection):

```
python core/TensorGuard.py pytorch 5 patch_level cot detection gpt-3.5-turbo
```
