import os
import shutil
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

load_dotenv()

VECTORSTORE_ROOT = "faiss_indexes"  # 👈 root directory containing all subject stores
TOPIC_FILE = "topics.txt"


def clear_all_faiss_vectorstores(root_path=VECTORSTORE_ROOT):
    """
    Deletes all FAISS vectorstore subdirectories under the given root.
    """
    if not os.path.exists(root_path):
        print(f"Vectorstore root '{root_path}' does not exist.")
        return

    removed = False
    for name in os.listdir(root_path):
        subdir = os.path.join(root_path, name)
        if os.path.isdir(subdir):
            shutil.rmtree(subdir)
            print(f"Deleted vectorstore: {subdir}")
            removed = True

    if removed:
        print("✅ All vectorstores cleared.")
    else:
        print("⚠️ No vectorstores found to delete.")


def print_all_faiss_vectorstores(root_path=VECTORSTORE_ROOT):
    """
    Loads and prints all FAISS vectorstores under the root folder.
    """
    if not os.path.exists(root_path):
        print(f"Vectorstore root '{root_path}' does not exist.")
        return

    embeddings = OpenAIEmbeddings()
    for name in os.listdir(root_path):
        subdir = os.path.join(root_path, name)
        index_file = os.path.join(subdir, "index.faiss")
        store_file = os.path.join(subdir, "index.pkl")

        if os.path.isdir(subdir) and os.path.exists(index_file) and os.path.exists(store_file):
            print(f"\n🔍 Vectorstore: {name}")
            db = FAISS.load_local(subdir, embeddings, allow_dangerous_deserialization=True)
            for i, (doc_id, doc) in enumerate(db.docstore._dict.items()):
                print(f"  Document {i+1} - ID: {doc_id}")
                print(f"    {doc.page_content[:150]}...")  # print first 150 chars
        else:
            print(f"\n⚠️ No FAISS index found in {subdir}")


if __name__ == "__main__":
    print("🔍 Current vectorstores:")
    print_all_faiss_vectorstores()

    print("\n🧹 Clearing ALL vectorstores...")
    clear_all_faiss_vectorstores()

    print("\n🔍 After clearing:")
    print_all_faiss_vectorstores()