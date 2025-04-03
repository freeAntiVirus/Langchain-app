import json
import os
import io
import base64
import re
import pdfplumber
from PIL import Image
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from openai import OpenAI
from langchain.schema import Document

load_dotenv()
app = FastAPI()
last_classified_images = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load topic list
with open("topics.txt", "r") as f:
    topic_text = f.read()

VECTORSTORE_PATH = "faiss_index"
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

# Load or initialize FAISS vectorstore
if os.path.exists(VECTORSTORE_PATH):
    vectorstore = FAISS.load_local(VECTORSTORE_PATH, OpenAIEmbeddings(), allow_dangerous_deserialization=True)
else:
    topic_docs = splitter.create_documents([topic_text])
    vectorstore = FAISS.from_documents(topic_docs, OpenAIEmbeddings())
    vectorstore.save_local(VECTORSTORE_PATH)

retriever = vectorstore.as_retriever()
client = OpenAI()

# Extract text from PDF pages
def extract_text_from_pdf(file_path):
    images = []
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            images.append({
                "id": f"page_{i+1}",
                "text": text,
                "topics": []
            })
    return images

# Extract images from PDF pages
def extract_images_from_pdf(file_path):
    images = []
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            img = page.to_image(resolution=200)
            pil_img = img.original
            

            buffered = io.BytesIO()
            pil_img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

            images.append({
                "id": f"page_{i+1}",
                "base64": img_str,
                "text": text,
                "topics": []
            })
    return images

# Classify an image using GPT-4o Vision
def classify_image_with_gpt(base64_img: str, topics_text: str, corrections_context: str):
    image_bytes = base64.b64decode(base64_img)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are an expert HSC Mathematics teacher."},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""
Classify this exam question into one or more topic codes.

❗ VERY IMPORTANT:
- Use only topic names from the official list — exactly as written.
- Do NOT invent, abbreviate, or shorten names.
- Do NOT say \"Financial Maths\" — use \"MA-M1: Modelling Financial Situations\"
- Do NOT say \"Probability\" — use \"MA-S1: Probability and Discrete Probability Distributions\"

"Here are semantically similar questions and how they were classified. Use them to guide your classification."
{corrections_context}

📋 OFFICIAL TOPIC LIST:
{topics_text}

Format:
{{ "topics": ["MA-F1: Working with functions"] }}
"""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_img}"
                        }
                    }
                ]
            }
        ],
        temperature=0
    )

    content = response.choices[0].message.content
    print("🧠 GPT Response:\n", content)
    try:
        match = re.search(r"{\s*\"topics\".*}", content, re.DOTALL)
        return json.loads(match.group(0)) if match else {"topics": []}
    except Exception as e:
        print("Failed to parse:", content)
        return {"topics": []}


@app.post("/classify/")
async def classify(file: UploadFile = File(...)):
    global last_classified_images
    file_path = f"temp_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    try:
        images = extract_images_from_pdf(file_path)

        new_docs = []
        for img in images:
            retrieved_docs = retriever.get_relevant_documents(img["text"])
            corrections_context = "\n\n".join(
    f"Question:\n{doc.page_content}\nTopics: {doc.metadata.get('topics', [])}"
    for doc in retrieved_docs
)

            result = classify_image_with_gpt(img["base64"], topic_text, corrections_context)
            img["topics"] = result.get("topics", [])

            doc = Document(
                page_content=img["text"],
                metadata={
                    "question_id": img["id"],
                    "topics": img["topics"],
                    "base64": img["base64"]
                }
            )
            new_docs.append(doc)

        vectorstore.add_documents(new_docs)
        vectorstore.save_local(VECTORSTORE_PATH)

        last_classified_images = images
        return {"result": images}
    finally:
        os.remove(file_path)

class Correction(BaseModel):
    id: str
    corrected_topics: List[str]


@app.post("/submit_corrections/")
async def submit_corrections(corrections: List[Correction]):
    # Update existing documents by replacing only the "topic" metadata
    updated_count = 0
    for correction in corrections:
        for doc_id, doc in vectorstore.docstore._dict.items():
            if doc.metadata.get("question_id") == correction.id:
                doc.metadata["topics"] = correction.corrected_topics
                updated_count += 1

    vectorstore.save_local(VECTORSTORE_PATH)

    print("\n📚 Updated vector store contents:")
    for i, doc in enumerate(vectorstore.docstore._dict.values()):
        print(f"{i+1}. ID: {doc.metadata.get('question_id')} | Topics: {doc.metadata.get('topics')} | Content: {doc.page_content}")

    return {"message": f"Corrections saved. Updated {updated_count} documents."}