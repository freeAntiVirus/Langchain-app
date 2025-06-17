import os
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings

def clear_faiss_vectorstore(index_path="faiss_index"):
    """
    Deletes the FAISS vector store files at the given path.
    """
    removed = False
    # FAISS typically saves two files: <index_path> and <index_path>.pkl
    print(os.listdir(index_path))
    for file in os.listdir(index_path):
        print(index_path + file)
        if os.path.exists(index_path + '/' + file):
            print(f"Deleting FAISS vector store file: {file}")
            os.remove(index_path + '/' + file)
            print(f"Deleted: {file}")
            removed = True
    if not removed:
        print("No FAISS vector store files found to delete.")
        
def print_faiss_vectorstore(index_path="faiss_index"):
    """
    Loads the FAISS vector store and prints the stored documents/texts.
    """
    # Initialize embeddings (use your actual embedding config if needed)
    embeddings = OpenAIEmbeddings()
    # Load the FAISS index
    db = FAISS.load_local(index_path, embeddings, allow_dangerous_deserialization=True)
    # Print all documents/texts
    for i, doc in enumerate(db.docstore._dict.values()):
        print(f"Document {i+1}:")
        print(doc.page_content)
        print("-" * 40)

if __name__ == "__main__":
    # Change 'faiss_index' to your actual index file name if different
    # clear_faiss_vectorstore("faiss_index")
    print_faiss_vectorstore("faiss_index")