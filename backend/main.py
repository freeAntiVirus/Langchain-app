import asyncio
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
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from openai import OpenAI
from langchain.schema import Document, HumanMessage
import pytesseract
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import ast
from typing import List, Optional
from pymongo import MongoClient
import random
from pdf2image import convert_from_path
from classification_utils import generate_unique_question_id
from db_utils import insert_classified_question

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

# Get MongoDB URI from .env
MONGO_URI = os.getenv("MONGO_URI")  # Format: mongodb+srv://user:pass@cluster0.mongodb.net/?retryWrites=true&w=majority

# Connect to MongoDB
client = MongoClient(MONGO_URI)
db = client["test_db"]

# Load topic list
with open("topics.txt", "r") as f:
    topic_text = f.read()

VECTORSTORE_PATH = "faiss_index"
splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

# Load or initialize FAISS vectorstore
if os.path.exists(VECTORSTORE_PATH):
    vectorstore = FAISS.load_local(VECTORSTORE_PATH, OpenAIEmbeddings(), allow_dangerous_deserialization=True)
else:
    print("No vectorstore found, rebuilding from MongoDB...")

    from langchain.schema import Document

    questions_col = db["questions"]
    all_questions = questions_col.find()

    docs = []
    for q in all_questions:
        # Safety check in case fields are missing
        if "text" in q and "QuestionId" in q:
            docs.append(Document(
                page_content=q["text"],
                metadata={
                    "question_id": q["QuestionId"],
                    "base64": q.get("base64", "")  # fallback to empty string if missing
                }
            ))

    if docs:
        vectorstore = FAISS.from_documents(docs, OpenAIEmbeddings())
        vectorstore.save_local(VECTORSTORE_PATH)
        print(f"Rebuilt vectorstore from {len(docs)} questions.")
    else:
        print("No questions found in DB — creating empty vectorstore.")
        vectorstore = FAISS.from_documents([Document(page_content="placeholder", metadata={})], OpenAIEmbeddings())
        vectorstore.docstore._dict.clear()
        vectorstore.index.reset()
        vectorstore.save_local(VECTORSTORE_PATH)


retriever = vectorstore.as_retriever()
client = OpenAI()


# NOTE: This is the new function that extracts images from files without any cropping logic
def extract_image_from_file(file_path):
    if file_path.lower().endswith(".pdf"):
        images = convert_from_path(file_path, dpi=200)
        image = images[0]  # Only use first page (or loop if you want all)
    else:
        image = Image.open(file_path)

    # Convert to base64
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

    # OCR
    text = pytesseract.image_to_string(image)

    # Generate unique ID
    existing_ids = {doc.metadata.get("question_id") for doc in vectorstore.docstore._dict.values()}
    qid = generate_unique_question_id(existing_ids)

    return [{
        "id": qid,
        "base64": img_str,
        "text": text,
        "topics": []
    }]

# Classify an image 
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
        images = extract_image_from_file(file_path)

        new_docs = []
        for img in images:

            # Check if this exact question already exists 
            # (CAN REMOVE THIS CHECK WHEN TESTING)
            duplicate_found = False
            for doc in vectorstore.docstore._dict.values():
               if doc.page_content.strip() == img["text"].strip():
                    reused_id = doc.metadata.get("question_id")
                    print(f"🔁 Reusing existing ID {reused_id} for duplicate")

                    # Fetch topics from MongoDB
                    topic_links = list(db["classification"].find({"QuestionId": reused_id}, {"_id": 0, "TopicId": 1}))
                    topic_ids = [t["TopicId"] for t in topic_links]

                    # Map topic IDs to human-readable names
                    topic_lookup = {
                        t["TopicId"]: t["name"]
                        for t in db["topics"].find({"TopicId": {"$in": topic_ids}}, {"_id": 0, "TopicId": 1, "name": 1})
                    }
                    full_topic_names = [topic_lookup.get(tid, tid) for tid in topic_ids]

                    img["id"] = reused_id
                    img["topics"] = full_topic_names
                    duplicate_found = True
                    break


            if duplicate_found:
                continue  #  Skip GPT and go to next image

            retrieved_docs = retriever.get_relevant_documents(img["text"])

            # Printing out the questions ai found semantically similar
            print("\n🔎 Retrieved relevant documents for this question:")
            for i, doc in enumerate(retrieved_docs):
                print(f"\nDoc {i+1}:")
                print(f"Text:\n{doc.page_content}")

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
            # insert_classified_question(img, db)

        if new_docs:
            vectorstore.add_documents(new_docs)
            vectorstore.save_local(VECTORSTORE_PATH)
        else:
            print("No new documents to add to vectorstore.")

        last_classified_images = images
        
        return {"result": images}
    finally:
        os.remove(file_path)

class ImageCorrection(BaseModel):
    id: str
    text: str
    base64: str
    topics: List[str]

@app.post("/submit_corrections/")
async def submit_corrections(images: List[ImageCorrection]):
    updated_count = 0
    for img in images:
        for doc_id, doc in vectorstore.docstore._dict.items():
            if doc.metadata.get("question_id") == img.id:
                doc.metadata["topics"] = img.topics
                updated_count += 1

        # ✅ Always insert/update in MongoDB
        insert_classified_question({
            "id": img.id,
            "text": img.text,
            "base64": img.base64,
            "topics": img.topics
        }, db)

    vectorstore.save_local(VECTORSTORE_PATH)

    return {"message": f"Corrections saved. Updated {updated_count} documents."}


class ImageData(BaseModel):
    base64: str
    id: str
    text: Optional[str]
    topics: Optional[List[str]]

class RevampRequest(BaseModel):
    img: ImageData

@app.post("/revamp_question/")
async def revamp_question(req: RevampRequest):
    img = req.img
    print("Received image:", img.text, img.topics)

    if not img.text or not img.topics:
        return JSONResponse(
            content={"error": "Original text or topics not found."},
            status_code=400
        )

    prompt = f"""
The original question was:
\"{img.text}\"

It was classified under the following topics:
{', '.join(img.topics)}

✅ Generate a **similar but different** HSC-style math question in proper **LaTeX format**.

Instructions:
- Target the **same topics**
- Do **NOT** include "Question X", "3 marks", "Office Use Only", or ID numbers
- Mimic the **structure and spacing** of the original question — if the original had parts on separate lines, maintain similar line separation
- If the question has parts (e.g. (a), (b)), split each part on a **new line**
- **Ignore any diagrams or image references** — do not include them
- DO NOT use `\\begin{{enumerate}}`, `\\item`, `\\begin{{tabular}}`, `\\begin{{center}}`, or any LaTeX commands unsupported by MathJax
- Use **\\( ... \\)** for inline math
- Use **\\[ ... \\]** or `\\begin{{align*}} ... \\end{{align*}}` for display math
- Only return the **question** – no explanations or commentary
- Output must be clean LaTeX, ready to render with MathJax
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a creative HSC Mathematics teacher who writes high-quality math questions in LaTeX."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    new_question_latex = response.choices[0].message.content.strip()

    return {
        "original_text": img.text,
        "topics": img.topics,
        "revamped_question_latex": new_question_latex
    }



class QuestionRequest(BaseModel):
    topics: List[str]
    count: int = 10

@app.post("/get-questions")
async def get_questions(req: QuestionRequest):
    topic_names = req.topics
    count = req.count

    # Step 1: Get Topic IDs for requested topic names
    topic_docs = list(db["topics"].find(
        {"name": {"$in": topic_names}}, {"_id": 0, "TopicId": 1}
    ))
    topic_ids = [t["TopicId"] for t in topic_docs]

    # Step 2: Find all matching Question IDs from classification
    classification_docs = list(db["classification"].find(
        {"TopicId": {"$in": topic_ids}}, {"_id": 0, "TopicId": 1, "QuestionId": 1}
    ))

    # Step 3: Map Question IDs to their associated Topic IDs
    question_map = {}
    for doc in classification_docs:
        qid = doc["QuestionId"]
        tid = doc["TopicId"]
        if qid not in question_map:
            question_map[qid] = set()
        question_map[qid].add(tid)

    # Step 4: Limit to desired number of questions
    question_ids = list(question_map.keys())[:count]

    # Step 5: Fetch full question data (text + base64)
    questions_data = list(db["questions"].find(
        {"QuestionId": {"$in": question_ids}},
        {"_id": 0, "QuestionId": 1, "base64": 1, "text": 1}
    ))

    # Step 6: Build topic lookup map
    topic_lookup = {
        t["TopicId"]: t["name"]
        for t in db["topics"].find({}, {"_id": 0, "TopicId": 1, "name": 1})
    }

    # Step 7: Construct final response objects
    final_questions = []
    for q in questions_data:
        qid = q["QuestionId"]
        topic_ids_for_q = question_map.get(qid, [])
        topics = [topic_lookup.get(tid, "Unknown Topic") for tid in topic_ids_for_q]

        final_questions.append({
            "id": qid,                       # required for revamp payload
            "QuestionId": qid,               # optional for frontend use
            "base64": q.get("base64", ""),   # base64 image
            "text": q.get("text", ""),       # original LaTeX text
            "topics": topics                 # human-readable topics
        })

    return JSONResponse(content={"questions": final_questions})
