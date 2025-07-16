import os
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter

load_dotenv()

VECTORSTORE_PATH = "faiss_index"
TOPIC_FILE = "topics.txt"
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

def clear_faiss_vectorstore(index_path=VECTORSTORE_PATH):
    """
    Deletes the FAISS vector store files at the given path.
    """
    if not os.path.exists(index_path):
        print("Vectorstore directory does not exist.")
        return
    removed = False
    for file in os.listdir(index_path):
        file_path = os.path.join(index_path, file)
        if os.path.isfile(file_path):
            os.remove(file_path)
            print(f"Deleted: {file_path}")
            removed = True
    os.rmdir(index_path)
    if removed:
        print("Vectorstore cleared.")
    else:
        print("No files found to delete in vectorstore.")

def print_faiss_vectorstore(index_path=VECTORSTORE_PATH):
    """
    Loads the FAISS vector store and prints the stored documents/texts.
    """
    index_file = os.path.join(index_path, "index.faiss")
    store_file = os.path.join(index_path, "index.pkl")
    
    if not os.path.exists(index_file) or not os.path.exists(store_file):
        print("No FAISS index found to load.")
        return

    embeddings = OpenAIEmbeddings()
    db = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
    for i, (doc_id, doc) in enumerate(db.docstore._dict.items()):
        print(f"Document {i+1} - ID: {doc_id}")
        print(doc.page_content)
        print("-" * 40)

if __name__ == "__main__":
    print("🔍 Initial vectorstore:")
    print_faiss_vectorstore()
    
    print("\n🧹 Clearing vectorstore...")
    clear_faiss_vectorstore()
    
    # print("\n📦 New vectorstore contents:")
    # print_faiss_vectorstore()
