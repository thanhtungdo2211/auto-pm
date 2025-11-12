from google import genai
from google.genai import types
import os 
from dotenv import load_dotenv
load_dotenv()

class GeminiEmbedding():
    def __init__(self):
        self.api_key_gemini = os.getenv("GEMINI_API_KEY")
        self.client = genai.Client(api_key = self.api_key_gemini)
    def embed_query(self, query):
        result = self.client.models.embed_content(
            model="gemini-embedding-001",
            contents=query,
            config=types.EmbedContentConfig(output_dimensionality=768))
        return result.embeddings[0].values
    
    def embed_documents(self, documents):
        result = self.client.models.embed_content(
            model="gemini-embedding-001",
            contents= documents,
            config=types.EmbedContentConfig(output_dimensionality=768))
        embeddings_list = [embedding.values for embedding in result.embeddings]
        return embeddings_list


from sentence_transformers import SentenceTransformer
from pyvi.ViTokenizer import tokenize  
class HuggingFaceEmbedding():
    def __init__(self):
        self.embed = SentenceTransformer("./models/vietnamese-embedding")
    def embed_query(self, query):
        tokenizer_sent = [tokenize(query)]
        result = self.embed.encode(tokenizer_sent)
        return result[0]
    
    def embed_documents(self, documents):
        tokenizer_sent = [tokenize(sent) for sent in documents]
        result = self.embed.encode(tokenizer_sent)
        return result


class SyncMessageService:
    def __init__(self):
        self.huggingfaceembedding = HuggingFaceEmbedding()
        self.geminiembedding = GeminiEmbedding()
    def embed_query(self, query: str):
        try: 
            embed = self.geminiembedding.embed_query(query)
            return embed
        except: 
            embed = self.huggingfaceembedding.embed_query(query)
            return embed
    def embed_documents(self, documents: list[str]):
        try: 
            embed = self.geminiembedding.embed_documents(documents)
            return embed
        except: 
            embed = self.huggingfaceembedding.embed_documents(documents)
            return embed
    
    def save_message(self, message: str, vector: list[float]):
        # Logic to save the message and its embedding vector to a database or storage
        pass
# Example usage