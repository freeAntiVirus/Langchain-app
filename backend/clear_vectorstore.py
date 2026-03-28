import os
import shutil
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

load_dotenv()

VECTORSTORE_ROOT = "faiss_indexes"
SOLUTIONS_VECTORSTORE_ROOT = "solutions"


def clear_vectorstore_root(root_path):
    """
    Deletes all FAISS vectorstore subdirectories under the given root.
    """
    if not os.path.exists(root_path):
        print(f"⚠️ Vectorstore root '{root_path}' does not exist.")
        return

    removed = False

    for name in os.listdir(root_path):
        subdir = os.path.join(root_path, name)

        if os.path.isdir(subdir):
            shutil.rmtree(subdir)
            print(f"Deleted vectorstore: {subdir}")
            removed = True

    if removed:
        print(f"✅ Cleared vectorstores under '{root_path}'")
    else:
        print(f"⚠️ No vectorstores found in '{root_path}'")


def print_all_faiss_vectorstores(root_path):
    """
    Loads and prints all FAISS vectorstores under the root folder.
    """
    if not os.path.exists(root_path):
        print(f"⚠️ Vectorstore root '{root_path}' does not exist.")
        return

    embeddings = OpenAIEmbeddings()

    for name in os.listdir(root_path):

        subdir = os.path.join(root_path, name)

        index_file = os.path.join(subdir, "index.faiss")
        store_file = os.path.join(subdir, "index.pkl")

        if os.path.isdir(subdir) and os.path.exists(index_file) and os.path.exists(store_file):

            print(f"\n🔍 Vectorstore: {root_path}/{name}")

            db = FAISS.load_local(
                subdir,
                embeddings,
                allow_dangerous_deserialization=True
            )

            for i, (doc_id, doc) in enumerate(db.docstore._dict.items()):
                print(f"  Document {i+1} - ID: {doc_id}")
                print(f"    {doc.page_content[:150]}...")

                if i >= 4:
                    break

        else:
            print(f"\n⚠️ No FAISS index found in {subdir}")


if __name__ == "__main__":

    print("🔍 Current question vectorstores:")
    print_all_faiss_vectorstores(VECTORSTORE_ROOT)

    print("\n🔍 Current solution vectorstores:")
    print_all_faiss_vectorstores(SOLUTIONS_VECTORSTORE_ROOT)

    print("\n🧹 Clearing question vectorstores...")
    clear_vectorstore_root(VECTORSTORE_ROOT)

    print("\n🧹 Clearing solution vectorstores...")
    clear_vectorstore_root(SOLUTIONS_VECTORSTORE_ROOT)

    print("\n🔍 After clearing:")
    print_all_faiss_vectorstores(VECTORSTORE_ROOT)
    print_all_faiss_vectorstores(SOLUTIONS_VECTORSTORE_ROOT)