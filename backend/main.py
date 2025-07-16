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

def generate_unique_question_id(existing_ids, max_tries=10):
    for _ in range(max_tries):
        qid = str(random.randint(100000, 999999))
        if qid not in existing_ids:
            return qid
    raise Exception("Failed to generate unique QuestionId after multiple attempts.")


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


def extract_text_with_ocr(pil_image):
    return pytesseract.image_to_string(pil_image)

#Extract images from PDF pages
# def extract_images_from_pdf(file_path):
#     images = []
#     with pdfplumber.open(file_path) as pdf:
#         for i, page in enumerate(pdf.pages):
#             img = page.to_image(resolution=200)
#             pil_img = img.original
#             text = extract_text_with_ocr(pil_img)
#             print("Extracted text:", text)
            

#             buffered = io.BytesIO()
#             pil_img.save(buffered, format="PNG")
#             img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

#             images.append({
#                 "id": f"page_{i+1}",
#                 "base64": img_str,
#                 "text": text,
#                 "topics": []
#             })
#     return images

def insert_classified_question(question_obj, db):
    """
    question_obj: {
        "id": "page_1_question_1",
        "text": "What is the derivative of x^2?",
        "base64": "<base64 string>",
        "topics": ["MA-C1", "MA-C2"]
            or
        "topics": ["MA-C1: Introduction to Differentiation (Year 11)"]
    }
    """
    questions_col = db["questions"]
    classifications_col = db["classification"]
   
    # try:
    existing = questions_col.find_one({"QuestionId": question_obj["id"]})
    
    if not existing:
        questions_col.insert_one({
            "QuestionId": question_obj["id"],
            "text": question_obj["text"],
            "base64": question_obj["base64"]
        })
        print(f"DB: Inserted question {question_obj['id']}")
    else:
        print(f"DB: Skipped — Question {question_obj['id']} already exists.")

    # Normalize topic strings to just "MA-XX" codes
    topic_ids = [topic.split(":")[0].strip() for topic in question_obj["topics"]]

    # Insert topic mappings
    # 🔄 Remove any existing mappings for this question
    classifications_col.delete_many({"QuestionId": question_obj["id"]})

    # 🔁 Insert fresh topic mappings
    for topic_id in topic_ids:
        classifications_col.insert_one({
            "QuestionId": question_obj["id"],
            "TopicId": topic_id
        })
        print(f"🔗 Mapped {question_obj['id']} to {topic_id}")



def extract_lines_with_coordinates(pil_img):
    ocr_data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT)
    lines = []
    current_line = ""
    last_line_num = -1
    last_block_num = -1
    last_top = -1

    for i in range(len(ocr_data['text'])):
        word = ocr_data['text'][i]
        if not word.strip():
            continue

        line_num = ocr_data['line_num'][i]
        block_num = ocr_data['block_num'][i]
        top = ocr_data['top'][i]

        if line_num != last_line_num or block_num != last_block_num:
            if current_line:
                lines.append((last_top, current_line.strip()))
            current_line = word
            last_top = top
        else:
            current_line += " " + word

        last_line_num = line_num
        last_block_num = block_num

    if current_line:
        lines.append((last_top, current_line.strip()))

    return lines


def extract_question_coordinates_from_lines(lines, openai_api_key):
    chat = ChatOpenAI(model_name="gpt-4", temperature=0, openai_api_key=openai_api_key)
    prompt = (
        "You are given a list of lines with their Y-coordinates from the top of a page.\n"
        "Identify the lines that mark the start of **new questions**.\n\n"

        "### Instructions:\n"
        "- If a line starts with a question number (e.g. 'Question 12 (3 marks)') or just a number like '12', and it is followed by lines continuing the prompt, only mark the first line. Do NOT mark those continuation lines as new questions — they are part of the same question block.\n"
        "- A question only ends when a new question starts \n"
        "- If a line contains only a question number (like '4' or 'Question 4') and is immediately followed by another line of text, treat both as the same question. Only mark the number line as the start.\n"
        "- Do NOT mark answer options like 'A.', 'B.', 'C.', or 'D.' as new questions.\n"
        "- Do NOT treat sub-parts like (a), (b), (c) as separate questions — they are part of the main question.\n"
        "- Use your reasoning: a question ends only after its options (if present) are listed, or when a completely new topic/question begins.\n\n"

        "Return a valid Python list of integers representing the **Y-coordinates** where new questions begin.\n"
        "Do not include any explanation. Do not include any question text.\n"
        "Example output: [100, 400, 700]\n\n"

        f"lines = {lines}"
    )

    response = chat([HumanMessage(content=prompt)])
    print("GPT Response:", response.content)

    try:
        result = ast.literal_eval(response.content)
        if isinstance(result, list) and all(isinstance(y, int) for y in result):
            return result
        else:
            print("Parsed result not valid:", result)
            return []
    except Exception as e:
        print("Failed to parse GPT output as list of Y-coordinates:", e)
        return []

def crop_image_by_y_coords(img, y_start, y_end):
    return img.crop((0, y_start, img.width, y_end))

def extract_text_with_ocr(pil_img):
    return pytesseract.image_to_string(pil_img)

def extract_images_from_pdf(file_path, openai_api_key):
    images = []
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            img = page.to_image(resolution=200).original

            lines = extract_lines_with_coordinates(img)

            print("Raw lines:", lines)
            y_coords = extract_question_coordinates_from_lines(lines, openai_api_key)
            print("Raw Y-coordinates:", y_coords)

            cropped_questions = []
            existing_ids = {doc.metadata.get("question_id") for doc in vectorstore.docstore._dict.values()}
            for idx, y_start in enumerate(y_coords):
                if idx + 1 < len(y_coords):
                    y_end = y_coords[idx + 1]
                else:
                    y_end = img.height

                leeway = 20
                y_start_leeway = max(y_start - leeway, 0)
                y_end_leeway = min(y_end, img.height)

                cropped_img = crop_image_by_y_coords(img, y_start_leeway, y_end_leeway)
                text = extract_text_with_ocr(cropped_img)
                buffered = io.BytesIO()
                cropped_img.save(buffered, format="PNG")
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

                qid = generate_unique_question_id(existing_ids)
                existing_ids.add(qid)
                cropped_questions.append({
                    "id": qid,
                    "base64": img_str,
                    "text": text,
                    "topics": []
                })

            images.extend(cropped_questions)
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
        images = extract_images_from_pdf(file_path, os.getenv("OPENAI_API_KEY"))

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