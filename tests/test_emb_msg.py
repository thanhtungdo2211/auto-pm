from langchain_huggingface import HuggingFaceEmbeddings
 
embeddings = HuggingFaceEmbeddings(model_name="VoVanPhuc/sup-SimCSE-VietNamese-phobert-base")

a = "This is a test sentence."

vector = embeddings.embed_query(a)
print(vector)
vector = embeddings.embed_documents([a])
print(vector)
def test_embed_query():
    from langchain_huggingface import HuggingFaceEmbeddings

    embeddings = HuggingFaceEmbeddings(model_name="VoVanPhuc/sup-SimCSE-VietNamese-phobert-base")

    a = "This is a test sentence."

    vector = embeddings.embed_query(a)
    assert isinstance(vector, list)
    assert all(isinstance(x, float) for x in vector)
    assert len(vector) > 0
def test_embed_documents():
    from langchain_huggingface import HuggingFaceEmbeddings

    embeddings = HuggingFaceEmbeddings(model_name="VoVanPhuc/sup-SimCSE-VietNamese-phobert-base")

    a = "This is a test sentence."

    vector = embeddings.embed_documents([a])
    assert isinstance(vector, list)
    assert len(vector) == 1
    assert all(isinstance(x, float) for x in vector[0])
    assert len(vector[0]) > 0   

if __name__ == "__main__":
    test_embed_query()
    test_embed_documents()
    