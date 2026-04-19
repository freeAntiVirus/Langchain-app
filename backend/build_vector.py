import os
import json
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

load_dotenv()

# ---- CONFIG ----
JSON_PATH = "solution/papers/solutions_output.json"
VECTORSTORE_PATH = "solutions/advanced"

# ---- INIT EMBEDDINGS ----
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")


# ---- LOAD JSON ----
def load_solutions(json_path):
    with open(json_path, "r") as f:
        data = json.load(f)
    return data


# ---- CONVERT TO DOCUMENTS ----
def build_documents(data):
    docs = []

    for item in data:
        # Main text that gets embedded
        content = item.get("SampleAnswer", "")

        # Metadata (VERY important for retrieval later)
        metadata = {
            "question_id": item.get("QuestionId"),
            "solution_id": item.get("SolutionId"),
            "criteria": item.get("Criteria"),
        }

        doc = Document(
            page_content=content,
            metadata=metadata
        )

        docs.append(doc)

    return docs


# ---- BUILD VECTORSTORE ----
def build_vectorstore(docs, save_path):
    print(f"📦 Building vectorstore with {len(docs)} documents...")

    vectorstore = FAISS.from_documents(docs, embeddings)

    # Save locally
    os.makedirs(save_path, exist_ok=True)
    vectorstore.save_local(save_path)

    print(f"✅ Vectorstore saved to: {save_path}")


# ---- MAIN ----
if __name__ == "__main__":
    data = load_solutions(JSON_PATH)
    docs = build_documents(data)
    build_vectorstore(docs, VECTORSTORE_PATH)