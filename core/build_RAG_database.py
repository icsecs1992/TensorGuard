import chromadb
from sentence_transformers import SentenceTransformer
from chromadb.api.types import Documents, EmbeddingFunction, Embeddings
import json, sys
from tqdm import tqdm

embedding_model = SentenceTransformer('all-MiniLM-L6-v2')

def load_json(data_path):
    with open(data_path) as json_file:
        data = json.load(json_file)
    return data

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

class MyEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input: Documents) -> Embeddings:
        batch_embeddings = embedding_model.encode(input)
        return batch_embeddings.tolist()

def prepare_batch_data(data, mode, code=True):
    
    batch_docs = []
    for item in data:
        if code:
            for change in item['changes']:
                if mode == 'patch_level':
                    for patch in change['patches']:
                        deleted_lines, added_lines = separate_added_deleted(patch['hunk'])
                        batch_docs.append(added_lines)
                else:
                    batch_docs.append(change['whole_hunk'])
        else:
            batch_docs.append(item["message"])

    return batch_docs

def make_basic_rag_db(lib, docs, mode='patch_level'):
    embed_fn = MyEmbeddingFunction()
    client = chromadb.PersistentClient(path='./docs_db')
    collection = client.get_or_create_collection(
        name=f"basic_rag_{mode}_{lib}",
    )
    
    batch_size = 50
    batch_docs = prepare_batch_data(docs, mode, code=True)
    for i in tqdm(range(0, len(batch_docs), batch_size)):
        batch = batch_docs[i : i + batch_size]
        batch_ids = [str(j+i) for j in range(len(batch))]
        # batch_ids = [str(item['Id']) for item in batch]
        # batch_metadata = [dict(label=doc["label"]) for doc in batch]
        
        batch_embeddings = embedding_model.encode(batch)
        
        collection.upsert(
            ids=batch_ids,
            # metadatas=batch_metadata,
            documents=batch,
            embeddings=batch_embeddings.tolist(),
        )
        
def test_inference(lib):
    embed_fn = MyEmbeddingFunction()
    client = chromadb.PersistentClient(path='./docs_db')
    collection = client.get_or_create_collection(
        name=f'basic_rag_{lib}',
        embedding_function=embed_fn
    )

    retriever_results = collection.query(
        query_texts=["fix out of bound bug"],
        n_results=1,
    )
    print(retriever_results["documents"])
    
def main(libname):
    mode = 'patch_level'
    docs = load_json(f'data/RAG_data/{libname}_rag_data.json')
    
    make_basic_rag_db(libname, docs, mode=mode)
    # test_inference(lib)
    
if __name__ == '__main__':
    libname = sys.argv[1]
    main(libname)