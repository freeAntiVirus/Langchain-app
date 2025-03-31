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

load_dotenv()
app = FastAPI()

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

# Extract images from PDF pages
def extract_images_from_pdf(file_path):
    images = []
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            img = page.to_image(resolution=200)
            pil_img = img.original

            buffered = io.BytesIO()
            pil_img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

            images.append({
                "id": f"page_{i+1}",
                "base64": img_str,
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

You can use these previous corrections for reference:
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
    file_path = f"temp_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    try:
        images = extract_images_from_pdf(file_path)
        retrieved_docs = retriever.get_relevant_documents("Classify HSC Maths questions")
        past_corrections = "\n".join(doc.page_content for doc in retrieved_docs)

        for img in images:
            result = classify_image_with_gpt(img["base64"], topic_text, past_corrections)
            print("✅ Classified:", result)
            img["topics"] = result.get("topics", [])

        return {"result": images}
    finally:
        os.remove(file_path)

class Correction(BaseModel):
    id: str
    corrected_topics: List[str]

@app.post("/submit_corrections/")
async def submit_corrections(corrections: List[Correction]):
    new_docs = []
    for correction in corrections:
        content = f"{correction.id} → {', '.join(correction.corrected_topics)}"
        new_docs.append(content)

    docs = splitter.create_documents(new_docs)
    vectorstore.add_documents(docs)
    vectorstore.save_local(VECTORSTORE_PATH)
    return {"message": "Corrections saved."}
