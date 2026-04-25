import asyncio
import json
import os
import io
import base64
import re
from PIL import Image
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from openai import OpenAI
from langchain_core.documents import Document
import pytesseract
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import ast
from typing import List, Optional
from pymongo import MongoClient
import random
from pdf2image import convert_from_path
from classification_utils import _stitch_double_spreads, _to_rgb, generate_unique_question_id, tally_topics
from db_utils import insert_classified_question
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from pathlib import Path
from collections import defaultdict
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
import os

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
db = client["hschub"]

# ---- Where to store each subject's FAISS index ----
VECTORSTORE_ROOT = Path("faiss_indexes")
VECTORSTORE_PATHS = {
    "Mathematics Advanced": VECTORSTORE_ROOT / "advanced",
    "Mathematics Standard": VECTORSTORE_ROOT / "standard",
    "Biology": VECTORSTORE_ROOT / "biology",
}

SOLUTIONS_VECTORSTORE_ROOT = Path("solutions")

SOLUTIONS_VECTORSTORE_PATHS = {
    "Mathematics Advanced": SOLUTIONS_VECTORSTORE_ROOT / "advanced",
    # "Mathematics Standard": SOLUTIONS_VECTORSTORE_ROOT / "standard",
    "Biology": SOLUTIONS_VECTORSTORE_ROOT / "biology",
}

SOLUTIONS_VECTORSTORE_ROOT.mkdir(parents=True, exist_ok=True)

VECTORSTORE_ROOT.mkdir(parents=True, exist_ok=True)

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
vectorstores = {}  # subject -> FAISS instance

# Helper: check if a FAISS index exists (folder + required files)
def _faiss_exists(folder: Path) -> bool:
    # FAISS saves multiple files; presence of index.faiss + index.pkl is typical.
    # If you want to be stricter, check for both.
    return (folder / "index.faiss").exists() and (folder / "index.pkl").exists()


def load_solutions_context_from_mongo():
    solutions_col = db["solutions"]

    docs = list(solutions_col.find({}, {"_id": 0}))

    # Convert to JSON string (same format as before)
    return json.dumps(docs, indent=2)

# SOLUTION VECTOR STORE
def build_solution_vectorstore(subject):

    path = SOLUTIONS_VECTORSTORE_PATHS[subject]

    solutions = list(db["solutions"].find(
    {"Subject": subject},   # ✅ FILTER
    {"_id": 0}
    ))

    docs = []

    for sol in solutions:

        content = f"""
Sample Answer:
{sol.get("SampleAnswer","")}

Criteria:
{sol.get("Criteria","")}

Diagram:
{sol.get("DiagramDescription","")}
"""

        doc = Document(
            page_content=content,
            metadata={
                "question_id": sol["QuestionId"],
                "solution_id": sol["SolutionId"],
                "criteria": sol.get("Criteria",""),
                "diagram": sol.get("DiagramDescription","")
            }
        )

        docs.append(doc)

    print(f"Building solutions FAISS for {subject} with {len(docs)} solutions...")

    vs = FAISS.from_documents(docs, embeddings)

    path.mkdir(parents=True, exist_ok=True)
    vs.save_local(str(path))

    return vs

# Try to load all three first
all_exist = all(_faiss_exists(p) for p in VECTORSTORE_PATHS.values())

if all_exist:
    for subj, path in VECTORSTORE_PATHS.items():
        vectorstores[subj] = FAISS.load_local(
            str(path),
            embeddings,
            allow_dangerous_deserialization=True,
        )
    print("Loaded all subject-specific vectorstores from disk.")
else:
    print("One or more vectorstores missing; rebuilding from MongoDB...")

    questions_col = db["questions"]
    classification_col = db["classification"]
    topics_col = db["topics"]

    # 0) Preload TopicId -> {name, subject}
    topics_by_id = {}
    for t in topics_col.find({}, {"_id": 0, "TopicId": 1, "name": 1, "subject": 1}):
        tid = str(t.get("TopicId"))
        if tid:
            topics_by_id[tid] = {
                "name": t.get("name", ""),
                "subject": t.get("subject", ""),
            }

    # 1) Build QuestionId -> [TopicId, ...]
    pipeline = [
        {
            "$group": {
                "_id": "$QuestionId",
                "topic_ids": {"$addToSet": "$TopicId"},
            }
        }
    ]
    topic_ids_by_qid = {}
    for row in classification_col.aggregate(pipeline):
        qid = str(row["_id"])
        topic_ids_by_qid[qid] = [
            str(tid) for tid in row.get("topic_ids", []) if tid is not None
        ]

    # 2) Build docs per subject
    docs_by_subject = defaultdict(list)  # subject -> [Document, ...]
    total_docs = 0

    for q in questions_col.find():
        if "text" in q and "QuestionId" in q:
            qid = str(q["QuestionId"])
            topic_ids = topic_ids_by_qid.get(qid, [])

            # Resolve TopicIds -> names/subjects
            topic_names = []
            subjects_for_q = set()
            for tid in topic_ids:
                meta = topics_by_id.get(tid)
                if meta:
                    # meta["name"] already includes the human string (e.g. "MA-F1: Working with Functions (Year 11)")
                    topic_names.append(meta["name"])
                    if meta.get("subject"):
                        subjects_for_q.add(meta["subject"])

            # If no subjects were resolved, you can choose to skip or bucket elsewhere
            if not subjects_for_q:
                # Optional: assign to a default bucket or continue
                # subjects_for_q.add("Unknown")  # if you want a catch-all
                continue

            doc = Document(
                page_content=q["text"],
                metadata={
                    "question_id": qid,
                    "topics": topic_names,  # human-friendly topic strings
                    "topic_ids": topic_ids, # raw TopicIds if useful
                    "base64": q.get("base64", ""),
                },
            )

            # Add the same doc to each subject this question belongs to
            for subj in subjects_for_q:
                if subj in VECTORSTORE_PATHS:  # only bucket known subjects
                    docs_by_subject[subj].append(doc)
                    total_docs += 1

    # 3) Build & persist FAISS per subject
    if any(docs_by_subject.values()):
        for subj, path in VECTORSTORE_PATHS.items():
            docs = docs_by_subject.get(subj, [])
            if not docs:
                print(f"[{subj}] No docs found — creating empty index.")
                # Create an empty FAISS with a placeholder, then clear it
                vs = FAISS.from_documents([Document(page_content="placeholder")], embeddings)
                vs.docstore._dict.clear()
                vs.index.reset()
            else:
                print(f"[{subj}] Building FAISS from {len(docs)} docs...")
                vs = FAISS.from_documents(docs, embeddings)

            path.mkdir(parents=True, exist_ok=True)
            vs.save_local(str(path))
            vectorstores[subj] = vs

        print(f"Rebuilt {len(vectorstores)} subject-specific vectorstores across {total_docs} docs.")
    else:
        print("No questions found with mapped subjects — creating empty indexes.")
        for subj, path in VECTORSTORE_PATHS.items():
            vs = FAISS.from_documents([Document(page_content="placeholder")], embeddings)
            vs.docstore._dict.clear()
            vs.index.reset()
            path.mkdir(parents=True, exist_ok=True)
            vs.save_local(str(path))
            vectorstores[subj] = vs

solution_vectorstores = {}

for subj in SOLUTIONS_VECTORSTORE_PATHS:
    path = SOLUTIONS_VECTORSTORE_PATHS[subj]

    if (path / "index.faiss").exists():

        solution_vectorstores[subj] = FAISS.load_local(
            str(path),
            embeddings,
            allow_dangerous_deserialization=True,
        )

        print(f"Loaded solution vectorstore for {subj}")

    else:

        solution_vectorstores[subj] = build_solution_vectorstore(subj)

client = OpenAI()


# NOTE: This is the new function that extracts images from files without any cropping logic
def extract_image_from_file(file_path, vs):
    if file_path.lower().endswith(".pdf"):
        # You can tweak dpi if needed (higher = bigger/clearer, but heavier)
        pages = convert_from_path(file_path, dpi=200)
        if len(pages) == 0:
            raise ValueError("PDF has no pages.")
        image = pages[0] if len(pages) == 1 else _stitch_double_spreads(pages, gap=32, bg_color="white")
    else:
        image = Image.open(file_path)
        image = _to_rgb(image)

    # Convert to base64 (PNG)
    buffered = io.BytesIO()
    image.save(buffered, format="PNG")
    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

    # OCR (run on the stitched image)
    text = pytesseract.image_to_string(image)

    # Generate unique ID
    existing_ids = {doc.metadata.get("question_id") for doc in vs.docstore._dict.values()}
    qid = generate_unique_question_id(existing_ids)

    return [{
        "id": qid,
        "base64": img_str,
        "text": text,
        "topics": []
    }]

def parse_topic_counts(s: str):
    """
    Parses a string like:
    'BIO-M5.4: Genetic Variation (Year 12): 8, BIO-M6.1: Mutation (Year 12): 8, ...'
    into a dictionary:
    {
        'BIO-M5.4: Genetic Variation (Year 12)': 8,
        'BIO-M6.1: Mutation (Year 12)': 8,
        ...
    }
    """
    counts = {}
    for part in s.split(","):
        part = part.strip()
        match = re.search(r":\s*(\d+)$", part)
        if not match:
            continue
        count = int(match.group(1))
        name = part[:match.start()].strip()
        counts[name] = count
    return counts
# Classify an image 
def classify_image_with_gpt(base64_img: str, topics_text: str, corrections_context: str):
    image_bytes = base64.b64decode(base64_img)
    print("CONTEXT",corrections_context)
    
    freq_counter = tally_topics(corrections_context)
    topic_counts_str = ", ".join([f"{topic}: {count}" for topic, count in freq_counter.most_common()])
    print("Topic counts:", topic_counts_str)

    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "topic_choice",
                "schema": {
                    "type": "object",
                    "properties": {
                        "topics": {
                            "type": "array",
                            "items": {
                                "type": "string",
                                "enum": list(parse_topic_counts(topic_counts_str).keys())
                            },
                            "minItems": 1
                        }
                    },
                    "required": ["topics"],
                    "additionalProperties": False
                },
            },
        },
        messages=[
            {"role": "system", "content": "You are an expert HSC Biology teacher."},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""
    {topic_counts_str}

    Classify this question using your reasoning **and** the topic rankings.
    - You must pick from the above topics only (no new ones).
    - Base your judgment on the question meaning first, then use the counts to break ties.

    📋 Allowed topics:
    {topic_counts_str}
    """
                    },
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{base64_img}" }},
                ],
            },
        ],
        temperature=0.3,
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
async def classify(file: UploadFile = File(...),  subject: str = Form(...)):
    global last_classified_images
    file_path = f"temp_{file.filename}"
    print(subject)
    vs = vectorstores[subject] 
    
    if subject is None or subject.strip() == "":
        raise HTTPException(status_code=400, detail="Missing 'subject' field in form data.")
    
    with open(file_path, "wb") as f:
        f.write(await file.read())

    try:
        
        # Query MongoDB for topics matching subject
        topic_docs = list(
            db["topics"].find(
                {"subject": subject},
                {"_id": 0, "TopicId": 1, "name": 1}
            ).sort("TopicId", 1)
        )

        # Format bullet list (but don’t return it)
        bullets = [
            f"* {t['TopicId']}: {t['name'].split(': ', 1)[1]}"
            if t["name"].startswith(t["TopicId"])
            else f"* {t['name']}"
            for t in topic_docs
        ]
        bullets_markdown = "\n".join(bullets)
        
        images = extract_image_from_file(file_path, vs)

        new_docs = []
        for img in images:

            # Check if this exact question already exists 
            duplicate_found = False
            for doc in vs.docstore._dict.values():
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
            
            retriever = vs.as_retriever(search_kwargs={"k": 150})
            retrieved_docs = retriever.invoke(img["text"])
            

            # DEBUG: Printing out the questions ai found semantically similar
            print("\n🔎 Retrieved relevant documents for this question:")
            for i, doc in enumerate(retrieved_docs):
                print(f"\nDoc {i+1}:")
                print(f"Text:\n{doc.page_content}")
                print(f"Topics: {doc.metadata.get('topics', [])}")

            corrections_context = "\n\n".join(
                f"Topics: {doc.metadata.get('topics', [])}"
                for doc in retrieved_docs
            )

            result = classify_image_with_gpt(img["base64"], bullets_markdown, corrections_context)
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

        if new_docs:
            vs.add_documents(new_docs)
            vs.save_local(str(VECTORSTORE_PATHS[subject]))
        else:
            print("No new documents to add to vectorstore.")

        last_classified_images = images
        
        return {"result": images}
    finally:
        os.remove(file_path)

# --- Pydantic models ---
class ImageCorrection(BaseModel):
    id: str
    text: Optional[str] = None
    base64: Optional[str] = None
    topics: List[str]

class SubmitCorrectionsPayload(BaseModel):
    subject: str
    corrections: List[ImageCorrection]

class GenerateSolutionRequest(BaseModel):
    question_text: str
    subject: str = "Mathematics Advanced"

@app.post("/submit_corrections/")
async def submit_corrections(payload: SubmitCorrectionsPayload):
    print("Received corrections payload:", payload)
    subject = payload.subject
    images = payload.corrections

    # pick the right FAISS index for this subject
    vs = vectorstores.get(subject)
    if vs is None:
        raise HTTPException(status_code=400, detail=f"No vectorstore found for subject '{subject}'")

    updated_count = 0
    added_count = 0

    # For quicker lookups, grab the dict once
    store_dict = vs.docstore._dict  # {doc_id: Document}

    for img in images:
        found_doc_id = None

        # 1) Update in-memory FAISS docstore if the doc exists
        for doc_id, doc in store_dict.items():
            if doc.metadata.get("question_id") == img.id:
                # update topics (and optional fields)
                doc.metadata["topics"] = img.topics
                if img.base64 is not None:
                    doc.metadata["base64"] = img.base64
                if img.text:  # if you also want to replace the content
                    doc.page_content = img.text
                found_doc_id = doc_id
                updated_count += 1
                break

        # 2) If not found in the FAISS store, optionally add it
        if found_doc_id is None and img.text:
            new_doc = Document(
                page_content=img.text,
                metadata={
                    "question_id": img.id,
                    "topics": img.topics,
                    "base64": img.base64 or "",
                },
            )
            vs.add_documents([new_doc])
            added_count += 1

        # 3) Always upsert to MongoDB
        insert_classified_question(
            {
                "id": img.id,
                "text": img.text,
                "base64": img.base64,
                "topics": img.topics,
                "subject": subject,  # keep subject alongside topics
            },
            db,
        )

    # persist ONLY this subject's FAISS index
    vs.save_local(str(VECTORSTORE_PATHS[subject]))

    return {
        "message": f"Corrections saved. Updated {updated_count} docs, added {added_count} new.",
        "subject": subject,
    }


class ImageData(BaseModel):
    base64: str
    id: str
    text: Optional[str]
    topics: Optional[List[str]]

class RevampRequest(BaseModel):
    img: ImageData
    subject: str
    
BIOLOGY_REVAMP_PROMPT = r"""
You are a Biology HSC question rewriter.

Your task is to revamp the given question to create ONE NEW UNIQUE question that tests the same concepts and remains consistent with the given question's difficulty, but 
uses a different scenario or different phrasing.

Question: 
{question_text}

Question topic(s):
{question_topics}

STRUCTURE RULES:
1) Keep the question in the same general format (e.g., multiple choice (a. b. c. d.), short answer, etc.).
3) Keep terminology and notation consistent with the subject area.
4) Avoid adding unrelated content or off-topic information.
5) Do NOT include marks, “Question X”, diagrams, page furniture, or IDs.

LATEX RULES:
- Use plain text for Biology unless referring to chemical/molecular notation (e.g., ATP, DNA, \(H_2O\)).
- Do NOT use LaTeX environments such as \begin{{align}}, TikZ, or tables.
Return only the raw question text (no explanations or commentary).
"""

MATH_REVAMP_PROMPT = r"""You are a HSC question rewriter that outputs questions in valid MathJax/KaTeX-safe LaTeX format.

Your task is to revamp the given question to create ONE NEW UNIQUE question that tests the same concepts and remains consistent with the given question's difficulty, but 
uses a different scenario or different phrasing.

Question: 
{question_text}

Question topic(s):
{question_topics}

STRUCTURE RULES:
1) Keep the question in the same general format (e.g., multiple choice (a. b. c. d.), short answer, etc.).
3) Keep terminology and notation consistent with the subject area.
4) Avoid adding unrelated content or off-topic information.
5) Do NOT include marks, “Question X”, diagrams, page furniture, or IDs.

LATEX RULES:
- Use only MathJax/KaTeX-safe LaTeX syntax.
- Inline math: \( ... \)
- Display math: \[ ... \] or \\begin{{align*}} ... \\end{{align*}}
- Do not use \\begin{{enumerate}}, \\item, \\tabular, \\center, TikZ, or \\boxed.
- Do not wrap LaTeX in triple backticks or prepend "latex".
- Return only the raw LaTeX content.

- Do not include explanations, reasoning, or extra commentary.
"""

@app.post("/revamp_question/")
async def revamp_question(req: RevampRequest):
    img = req.img
    subject = req.subject
    print("WOWOWW",subject)
    print("Received image:", img.text, img.topics)

    if not img.text or not img.topics:
        return JSONResponse(
            content={"error": "Original text or topics not found."},
            status_code=400
        )

      # Format the prompt
    if req.subject == "Biology":
        prompt_template = BIOLOGY_REVAMP_PROMPT
    else: 
        prompt_template = MATH_REVAMP_PROMPT

    user_prompt = prompt_template.format(
        question_text = img.text,
        question_topics = img.topics
    )
    print(user_prompt)
    prompt = user_prompt
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a creative HSC teacher who writes high-qualit HSC questions in LaTeX."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.7
    )

    new_question_latex = response.choices[0].message.content.strip()
    print(new_question_latex)
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

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from openai import OpenAI
import os
import asyncio
from pymongo import MongoClient
from schemas import GenerateFromTopicsRequest, GenerateFromTopicsResponse
from db_utils import fetch_questions_with_all_topics


SYSTEM_PROMPT = (
    "You are a senior HSC Mathematics teacher who writes authentic HSC-style questions in LaTeX."
)

USER_PROMPT_TEMPLATE = r"""You are given authentic HSC exemplar questions. 
Your task is to write ONE NEW UNIQUE HSC-style question that looks and feels like these exemplars.

The topics are provided only to keep the mathematics relevant.
Do NOT use different technical terminology, or invent your own structure or style — stay as close as possible to the exemplars.
Randomise the difficulty of the questions you generate (not always very easy, make some quite hard).

Exemplar questions (Use as reference for style, structure, and phrasing):
{exemplars_block}

Target topics (for relevance only, secondary to style):
{topics_lines}

Write EXACTLY ONE HSC-style math question.

STRUCTURE RULES:
1) Begin with ONE common stem (e.g., a function, a graph, a scenario).
2) If there are multiple tasks, split into (a), (b), (c) — but ONLY if they naturally follow from the stem. 
   - If a single task is sufficient, write only one task (no unnecessary parts).
   - If multiple parts are used, each must depend on the stem and logically follow from the previous.
3) Do NOT introduce unrelated functions or new scenarios.
4) Do NOT include marks, “Question X”, diagrams, page furniture, or IDs.

LATEX RULES:
- Use only MathJax/KaTeX-safe LaTeX:
  - Inline: \( ... \)
  - Display: \[ ... \] or \begin{{align*}}...\end{{align*}}
- Do NOT use \begin{{enumerate}}, \item, \tabular, \center, TikZ, or \boxed.
- Do NOT wrap in triple backticks or prepend "latex".
Return only the raw LaTeX content.
"""

BIOLOGY_USER_PROMPT_TEMPLATE = r"""You are given authentic HSC Biology exemplar questions. 
Your task is to write ONE NEW UNIQUE HSC-style question that looks and feels like these exemplars.

The topics are provided only to keep the biology content relevant.
Do NOT use terminology or structures that differ from authentic HSC Biology exam style.
Questions must sound natural and realistic for NESA-style HSC exams, not textbook exercises.

Exemplar questions (pick a random one and use it as the main reference for style, structure, and phrasing):
{exemplars_block}

Target topics (for relevance only, secondary to style):
{topics_lines}

Write EXACTLY ONE HSC-style Biology question.

STRUCTURE RULES:
1) Begin with ONE clear scenario, diagram description, experiment, or context.
2) Follow with one or more tasks labelled (a), (b), (c), only if necessary.
   - Each part must follow logically from the stem.
   - Avoid unnecessary multi-part structures if one question is sufficient.
3) Use natural scientific phrasing, focusing on explanation, analysis, or evaluation.
4) Align with HSC Biology command verbs such as: "explain", "analyse", "assess", "evaluate", "describe", "justify", or "outline".
5) Do NOT include marks, “Question X”, diagrams, page furniture, or IDs.

CONTENT RULES:
- Keep all content scientifically accurate.
- Use realistic biological examples (e.g., pathogens, enzymes, DNA processes, immune response).
- Do NOT include fictitious data, irrelevant scenarios, or diagrams.
- Avoid numerical or mathematical style wording.

LATEX RULES:
- Use plain text for Biology unless referring to chemical/molecular notation (e.g., ATP, DNA, \(H_2O\)).
- Do NOT use LaTeX environments such as \begin{{align}}, TikZ, or tables.

Return only the raw question text (no explanations or commentary).
"""

def _topics_lines(topics):
    return "\n".join(f"- {t}" for t in topics)

def _exemplars_block(docs):
    blocks = []
    for i, d in enumerate(docs, 1):
        # prefer stored LaTeX if you have it, fall back to text
        body = (d.get("latex") or d.get("text") or "").strip()
        if not body:
            # You can also OCR base64 later if needed, but we’ll skip empties.
            continue
        blocks.append(f"--- Exemplar {i} ---\n{body}")
    return "\n\n".join(blocks)

@app.post("/generate-question-by-topics", response_model=GenerateFromTopicsResponse)
async def generate_question_by_topics(req: GenerateFromTopicsRequest):
    topics = [t.strip() for t in req.topics if t.strip()]
    if not topics:
        return JSONResponse({"error": "At least one topic is required."}, status_code=400)

    # Pull intersection exemplars from Mongo
    exemplars = fetch_questions_with_all_topics(
        db, topic_names=topics, limit=req.exemplar_count
    )

    # Require ≥2 exemplars to properly ground the style
    if len(exemplars) < 1:
        return JSONResponse(
            {"error": "Not enough questions match ALL selected topics. Try fewer/different topics."},
            status_code=404
        )

    subject = getattr(req, "subject", "").lower().strip()
    if subject == "biology":
        prompt_template = BIOLOGY_USER_PROMPT_TEMPLATE
    else:
        prompt_template = USER_PROMPT_TEMPLATE

    # Format the prompt
    user_prompt = prompt_template.format(
        topics_lines=_topics_lines(topics),
        exemplars_block=_exemplars_block(exemplars),
    )
    
    print("User prompt:\n", user_prompt)

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        temperature=req.temperature,
        max_tokens=700,
    )

    latex = resp.choices[0].message.content.strip()
    response = {
        "topics": topics,
        "exemplars_used": len(exemplars),
        "latex": latex,
        "exemplar_ids": [q["QuestionId"] for q in exemplars],
    }
    
    print("ids", response["exemplar_ids"])
    return response

# add to your existing file (same imports stay)
from typing import Optional, Literal
from pydantic import BaseModel
import tempfile
import subprocess
import shutil
import textwrap
import uuid
import os

# ---------- Pydantic Schemas ----------

class GenerateDiagramRequest(BaseModel):
    question_latex: str                     # the LaTeX you just generated
    topics: Optional[list[str]] = None      # optional, helps the model choose diagram type
    render_target: Literal["tikz", "svg"] = "tikz"  # "tikz" (client-side tikzjax) or "svg" (server-side compile)
    temperature: float = 0.2                # diagrams should be deterministic-ish
    # optional high-level hints (e.g., "plot the cubic", "right-angled triangle with altitude")
    hint: Optional[str] = None

class GenerateDiagramResponse(BaseModel):
    tikz_code: str                          # always returned (inside \begin{tikzpicture}...\end{tikzpicture})
    svg: Optional[str] = None               # returned only if render_target="svg" and compile succeeds
    warnings: Optional[list[str]] = None

# ---------- Prompts ----------

SYSTEM_PROMPT_DIAGRAM = (
    "You are a senior HSC Mathematics teacher and LaTeX/TikZ expert. "
    "You generate clear, syllabus-aligned TikZ diagrams that match exam style."
)

USER_PROMPT_TEMPLATE_DIAGRAM = r"""
You are given an HSC-style math question in LaTeX (no solutions provided).

Your task:
1) Decide whether a diagram meaningfully supports the question (axes, graph, labelled points,
   geometric figure, vector diagram, probability tree, etc).
2) If yes, output ONLY a valid TikZ diagram inside EXACTLY one environment:
   \begin{{tikzpicture}}
     ...
   \end{{tikzpicture}}

Constraints:
- Use TikZ primitives that are compatible with tikzjax or standalone->dvisvgm: no external images, no PGFPlots.
- If axes are needed, draw them with ticks and labels; label key points/curves clearly.
- Keep exam style: clean, uncluttered, black/white lines, sensible scales.
- DO NOT include preamble, \documentclass, \usepackage, or \begin{{document}}.
- DO NOT include any text besides the tikzpicture environment.
- If a diagram is unnecessary, still produce a minimal contextual diagram (e.g., axes with a placeholder curve) that remains useful.
- ALWAYS restrict the domain of any plotted function (e.g. domain=-2:3).
- Ensure all graphs are bounded within a visible window.
- Do NOT draw curves that extend infinitely beyond the axes.
- Keep the entire diagram within a reasonable box (based on context).
- Give appropriate space for tree diagrams and use small labels or legends if needed.

Question (LaTeX):
---
{question_latex}
---

Topics (optional): 
{topics_lines}

Design hint (optional):
{hint_line}
"""

def _topics_lines_for_diagram(topics: Optional[list[str]]) -> str:
    if not topics:
        return "(none)"
    return "\n".join(f"- {t}" for t in topics)

def _hint_line(hint: Optional[str]) -> str:
    return hint if hint else "(none)"

# ---------- TikZ -> SVG (optional server-side compile) ----------

import os, shutil, tempfile, textwrap, subprocess
from typing import Optional, Tuple

def tikz_to_svg(tikz_code: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Compile TikZ to SVG using:
      1) tectonic -> PDF
      2) dvisvgm --pdf  (needs Ghostscript)
      3) pdftocairo -svg (Poppler)
      4) inkscape --export-type=svg
    Returns (svg_text, warning) where one may be None.
    """
    warnings = []

    def which(name): return shutil.which(name)

    has_tectonic  = bool(which("tectonic"))
    has_dvisvgm   = bool(which("dvisvgm"))
    has_gs        = bool(which("gs"))            # Ghostscript
    has_pdftocairo= bool(which("pdftocairo"))    # Poppler
    has_inkscape  = bool(which("inkscape"))

    if not has_tectonic:
        print("SVG conversion skipped: tectonic not found.")
        return None, "SVG: tectonic not found on server."

    tmpdir = tempfile.mkdtemp(prefix="tikzsvg_")
    try:
        # --- Write minimal standalone TeX ---
        tex = textwrap.dedent(f"""
        \\documentclass[tikz,border=2pt]{{standalone}}
        \\usepackage{{tikz}}
        \\begin{{document}}
        {tikz_code}
        \\end{{document}}
        """).strip()
        with open(os.path.join(tmpdir, "fig.tex"), "w", encoding="utf-8") as f:
            f.write(tex)

        # --- 1) tectonic -> PDF ---
        tect = subprocess.run(
            ["tectonic", "--keep-logs", "--keep-intermediates", "fig.tex"],
            cwd=tmpdir, capture_output=True, text=True, timeout=60
        )
        if tect.returncode != 0:
            return None, f"SVG: tectonic error: {tect.stderr.strip()[:2000]}"

        pdf_path = os.path.join(tmpdir, "fig.pdf")
        if not os.path.exists(pdf_path) or os.path.getsize(pdf_path) == 0:
            log_tail = ""
            log_path = os.path.join(tmpdir, "fig.log")
            if os.path.exists(log_path):
                with open(log_path, "r", encoding="utf-8", errors="ignore") as lf:
                    log_tail = lf.read()[-2000:]
            return None, "SVG: PDF not produced by tectonic. " + (f"Log tail: {log_tail}" if log_tail else "")

        print("IM IN HERE")

        # --- 2) dvisvgm --pdf (preferred) ---
        if has_dvisvgm:
            print("Using dvisvgm for PDF->SVG conversion.")
            if not has_gs:
                warnings.append("SVG: Ghostscript (gs) not found; dvisvgm --pdf may fail.")
            dsvg = subprocess.run(
                ["dvisvgm", "--no-fonts", "--exact", "--pdf", "fig.pdf", "--page=1-", "-o", "fig.svg"],
                cwd=tmpdir, capture_output=True, text=True, timeout=60
            )
            if dsvg.returncode == 0 and os.path.exists(os.path.join(tmpdir, "fig.svg")):
                with open(os.path.join(tmpdir, "fig.svg"), "r", encoding="utf-8") as f:
                    return f.read(), (warnings[0] if warnings else None)
            else:
                warnings.append(f"SVG: dvisvgm error: {dsvg.stderr.strip()[:2000]}")

        # --- 3) Poppler: pdftocairo -svg (very reliable) ---
        if has_pdftocairo:
            svg_out = os.path.join(tmpdir, "fig.svg")
            pc = subprocess.run(
                ["pdftocairo", "-svg", "fig.pdf", "fig.svg"],
                cwd=tmpdir, capture_output=True, text=True, timeout=60
            )
            if pc.returncode == 0 and os.path.exists(svg_out):
                with open(svg_out, "r", encoding="utf-8") as f:
                    return f.read(), ("; ".join(warnings) if warnings else None)
            else:
                warnings.append(f"SVG: pdftocairo error: {pc.stderr.strip()[:2000]}")

        # --- 4) Inkscape fallback ---
        if has_inkscape:
            svg_out = os.path.join(tmpdir, "fig.svg")
            inks = subprocess.run(
                ["inkscape", "--export-type=svg", "--export-filename=fig.svg", "fig.pdf"],
                cwd=tmpdir, capture_output=True, text=True, timeout=60
            )
            if inks.returncode == 0 and os.path.exists(svg_out):
                with open(svg_out, "r", encoding="utf-8") as f:
                    return f.read(), ("; ".join(warnings) if warnings else None)
            else:
                warnings.append(f"SVG: inkscape error: {inks.stderr.strip()[:2000]}")

        # Nothing worked → signal fallback to TikZ
        warn = "; ".join(warnings) if warnings else "SVG: conversion failed; no converter available."
        return None, warn

        print("SVG GENERATED:", svg_text is not None)
        print("WARNINGS:", warnings)

    except subprocess.TimeoutExpired:
        return None, "SVG: conversion timed out."
    except Exception as e:
        return None, f"SVG: unexpected failure: {e}"
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

# ---------- Endpoint ----------

@app.post("/generate-diagram-for-question", response_model=GenerateDiagramResponse)
async def generate_diagram_for_question(req: GenerateDiagramRequest):
    user_prompt = USER_PROMPT_TEMPLATE_DIAGRAM.format(
        question_latex=req.question_latex.strip(),
        topics_lines=_topics_lines_for_diagram(req.topics),
        hint_line=_hint_line(req.hint)
    )

    chat = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT_DIAGRAM},
            {"role": "user", "content": user_prompt},
        ],
        temperature=req.temperature,
        max_tokens=900,
    )

    raw = (chat.choices[0].message.content or "").strip()

    # Sanity: extract exactly one tikzpicture block
    start_tag = r"\begin{tikzpicture}"
    end_tag = r"\end{tikzpicture}"
    start_idx = raw.find(start_tag)
    end_idx = raw.rfind(end_tag)

    tikz_code = raw[start_idx:end_idx + len(end_tag)]
    warnings = None

    svg_text = None
    if req.render_target == "svg":
        svg_text, warn = tikz_to_svg(tikz_code)
        if warn:
            warnings = (warnings or []) + [warn]

    return GenerateDiagramResponse(
        tikz_code=tikz_code,
        svg=svg_text,
        warnings=warnings
    )

def main():
    import asyncio
    import os
    import webbrowser

    # Try optional PNG export if cairosvg is available
    try:
        import cairosvg  # pip install cairosvg
        CAIROS_SVG_OK = True
    except Exception:
        CAIROS_SVG_OK = False

    # Sample LaTeX question (use one you just generated if you like)
    sample_question = r"""
    A function is defined by \( f(x) = x^2 - 4x + 3 \).
    (a) Sketch the graph of \( f(x) \) for \( -1 \leq x \leq 5 \).
    (b) Find the coordinates of the turning point.
    """

    req = GenerateDiagramRequest(
        question_latex=sample_question,
        topics=["MA-C3: Applications of Differentiation (Year 12)"],
        render_target="svg",   # IMPORTANT: ask the API to return SVG
        temperature=0.2,
        hint="Include axes, label the turning point, and show the parabola clearly."
    )

    async def run_test():
        result = await generate_diagram_for_question(req)

        # Always print the TikZ for debugging
        print("\n--- TikZ Code ---\n")
        print(result.tikz_code)

        # Ensure we actually got an SVG back
        svg_text = result.svg
        if not svg_text:
            print("\n(No SVG returned — set render_target='svg' or ensure server has 'tectonic' and 'dvisvgm'.)")
            if result.warnings:
                print("Warnings:", result.warnings)
            return

        # Save SVG
        svg_path = os.path.abspath("diagram.svg")
        with open(svg_path, "w", encoding="utf-8") as f:
            f.write(svg_text)
        print(f"\nSaved SVG → {svg_path}")

        # Optionally export PNG if cairosvg is available
        if CAIROS_SVG_OK:
            png_path = os.path.abspath("diagram.png")
            try:
                cairosvg.svg2png(bytestring=svg_text.encode("utf-8"), write_to=png_path, dpi=144)
                print(f"Saved PNG → {png_path}")
            except Exception as e:
                print(f"(PNG export failed via cairosvg: {e})")
                png_path = None
        else:
            png_path = None
            print("(cairosvg not installed — skipping PNG export. pip install cairosvg)")

        # Try to open the image automatically (prefer PNG if available)
        open_path = png_path or svg_path
        try:
            webbrowser.open(f"file://{open_path}")
            print(f"Opened → {open_path}")
        except Exception as e:
            print(f"(Could not auto-open file: {e})")

        # Print any warnings from the endpoint
        if result.warnings:
            print("\n--- Warnings ---\n")
            for w in result.warnings:
                print("-", w)

    asyncio.run(run_test())

# GENERATE SOLUTIONS 
def extract_question_text_from_base64(image_base64: str):

    prompt = "Extract the exact question text from this image."

    response = client.responses.create(
        model="gpt-5.2",
        input=[
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": prompt},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{image_base64}"
                    }
                ]
            }
        ]
    )

    return response.output_text.strip()

def retrieve_similar_solutions(question_text, subject, k=5):

    vs = solution_vectorstores.get(subject)

    if vs is None:
        raise HTTPException(status_code=400, detail=f"No solution vectorstore for {subject}")

    retriever = vs.as_retriever(search_kwargs={"k": k})
    docs = retriever.invoke(question_text)

    return docs

def generate_solution_from_text(question_text: str, subject: str):

    # 1. Retrieve similar solutions (RAG)
    docs = retrieve_similar_solutions(question_text, subject)

    # Debug (optional)
    for d in docs:
        print("Retrieved:", d.metadata)

    # 2. Build context
    solutions_context = "\n\n".join([
        f"""
--- Solution Reference ---
{d.page_content}
"""
        for d in docs
    ])

    # 3. Prompt construction
    if subject == "Biology":

        system_prompt = """You are an NSW HSC Biology exam marker.

Your task is to generate answers in the SAME style as official HSC sample solutions.

Rules:
• Use concise biological terminology
• Follow marking criteria structure
• Match HSC command verbs (explain, analyse, evaluate)
- Do not use technical language or phrasing that differs from authentic HSC Biology exam style or is outside the scope of typical HSC questions.
"""

        user_prompt = f"""
You are given HSC Biology sample answers and marking criteria.

Reference solutions:
{solutions_context}

Using the SAME style:
- Use precise biological terminology
- Follow marking criteria wording
- Be concise but complete
- Use appropriate command verbs (explain, analyse, evaluate)

Question:
{question_text}

Format your response EXACTLY like this:

SOLUTION:
<full worked solution>
"""

    else:  # Mathematics

        latex_rules = """
LATEX RULES:
- Use only MathJax/KaTeX-safe LaTeX:
  - Inline: \( ... \)
  - Display: \[ ... \] or \begin{{align*}}...\end{{align*}}
- Do NOT use \begin{{enumerate}}, \item, \tabular, \center, TikZ, or \boxed.
- Do NOT wrap in triple backticks or prepend "latex".
Return only the raw LaTeX content.

"""

        system_prompt = """You are an experienced NSW HSC Mathematics teacher.

Your goal is to produce clear, structured solutions that help students learn.

STYLE:
- Follow HSC exam structure
- Show full working clearly
- Include brief explanations to justify each step
- Use concise, student-friendly language
- Avoid unnecessary wording, but do not remove important reasoning
- Ensure each step logically follows from the previous one

LEVEL CONSTRAINT (VERY IMPORTANT):

- All solutions must be strictly within the NSW HSC Mathematics Advanced syllabus
- Do NOT use university-level concepts, terminology, or reasoning
- Do NOT include abstract or theoretical explanations
- Use only methods and language that a Year 12 student is expected to know
- If a method is not part of the HSC syllabus, do not use it
"""

        user_prompt = f"""
Use the marking style and structure of the reference solutions.

Reference solutions:
{solutions_context}

Now solve the following question in HSC exam style.

{latex_rules}

Question:
{question_text}

FORMAT:

SOLUTION:

- Present working step-by-step
- Include brief explanations where needed to explain reasoning
- Use clear mathematical structure (align steps logically)
- Final answers should be clearly stated
- Do not center or box answers; use standard aligned equations and clear step-by-step working.
"""

    # 4. Call model
    response = client.responses.create(
        model="gpt-5.2",
        temperature=0.2,
        input=[
            {
                "role": "system",
                "content": [{"type": "input_text", "text": system_prompt}]
            },
            {
                "role": "user",
                "content": [{"type": "input_text", "text": user_prompt}]
            }
        ]
    )

    # Debug output
    print("\n--- RETRIEVED SOLUTIONS ---\n")
    for i, d in enumerate(docs):
        print(f"\nSolution {i+1}")
        print(d.page_content[:200])

    return response.output_text


def generate_solution_from_image(image_base64: str, subject: str):

    if subject == "Biology":

        system_prompt = """You are an NSW HSC Biology exam marker.

Generate answers in official HSC sample solution style.

Rules:
• Use concise biological terminology
• Follow marking criteria structure
• Match command verbs (explain, analyse, evaluate)
"""

        user_prompt = """
You are given an exam question as an image.

Read the question carefully and generate a full HSC-style solution.

Format:

SOLUTION:
<full answer>
"""

    else:  # Mathematics

        latex_rules = """
LATEX RULES:
- Use only MathJax/KaTeX-safe LaTeX:
  - Inline: \( ... \)
  - Display: \[ ... \] or \begin{{align*}}...\end{{align*}}
- Do NOT use \begin{{enumerate}}, \item, \tabular, \center, TikZ, or \boxed.
- Do NOT wrap in triple backticks or prepend "latex".
Return only the raw LaTeX content.
"""

        system_prompt = """You are an NSW HSC Mathematics marker.

STRICT RULES:
• Answer all parts
• No long explanations
• Only exam-style working
• No unnecessary words
• Show only steps that earn marks
"""

        user_prompt = f"""
You are given a maths exam question as an image.

Solve it in HSC exam style.

{latex_rules}

Format:

SOLUTION:
<step-by-step working>
"""

    response = client.responses.create(
        model="gpt-5.2",
        temperature=0.2,
        input=[
            {
                "role": "system",
                "content": [{"type": "input_text", "text": system_prompt}]
            },
            {
                "role": "user",
                "content": [
                    {"type": "input_text", "text": user_prompt},
                    {
                                        
                    "type": "input_image",
                    "image_url": f"data:image/png;base64,{image_base64}"
                    }
                ]
            }
        ]
    )

    return response.output_text


class GenerateSolutionRequest(BaseModel):
    question_text: str
    subject: str

@app.post("/generate-solution-text")
async def generate_solution_endpoint(req: GenerateSolutionRequest):

    print("Generating solution for subject:", req.subject)
    try:
        result_text = generate_solution_from_text(req.question_text, req.subject)

        print("\n--- RAW MODEL OUTPUT ---\n")
        print(result_text)

        solution_match = re.search(r"SOLUTION:\s*(.*)", result_text, re.DOTALL)

        generated_solution = (
            solution_match.group(1).strip()
            if solution_match
            else result_text.strip()
        )
        return {
            "generated_solution": generated_solution,
        }

    except Exception as e:
        print("🔥 ERROR:", str(e))
        traceback.print_exc()   # THIS IS CRITICAL
        raise HTTPException(status_code=500, detail=str(e))


class GenerateImageSolutionRequest(BaseModel):
    image_base64: str
    subject: str

@app.post("/generate-solution-image")
async def generate_solution_endpoint(req: GenerateImageSolutionRequest):

    print("Generating solution for subject:", req.subject)
    try:
        result_text = generate_solution_from_image(req.image_base64, req.subject)

        print("\n--- RAW MODEL OUTPUT ---\n")
        print(result_text)

        solution_match = re.search(r"SOLUTION:\s*(.*)", result_text, re.DOTALL)

        generated_solution = (
            solution_match.group(1).strip()
            if solution_match
            else result_text.strip()
        )
        return {
            "generated_solution": generated_solution,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class GenerateFeedbackRequest(BaseModel):
    image_base64: str
    question_text: str
    subject: str = "Mathematics Advanced"

from fastapi import HTTPException
from pydantic import BaseModel
import json

class GenerateFeedbackRequest(BaseModel):
    image_base64: str
    question_text: str
    subject: str = "Mathematics Advanced"


@app.post("/generate_feedback")
async def generate_feedback(req: GenerateFeedbackRequest):

    try:
        # ==============================
        # 1. OCR: Extract student solution
        # ==============================
        extraction_prompt = """
Extract ONLY the student's FULL working/solution.

Return STRICT JSON:
{
  "student_solution": "..."
}
"""

        extraction = client.responses.create(
            model="gpt-5.2",
            input=[{
                "role": "user",
                "content": [
                    {"type": "input_text", "text": extraction_prompt},
                    {
                        "type": "input_image",
                        "image_url": f"data:image/png;base64,{req.image_base64}"
                    }
                ]
            }]
        )

        extracted_text = extraction.output_text.strip()

        try:
            parsed = json.loads(extracted_text)
            student_solution = parsed["student_solution"]
        except:
            raise HTTPException(status_code=500, detail="Failed to parse OCR output")

        print("\n📝 STUDENT SOLUTION:\n", student_solution)


        # ==============================
        # 2. Retrieve similar solutions (IMPROVED QUERY)
        # ==============================

        if "biology" in req.subject.lower():
            query = f"""
        HSC Biology question involving:
        - key biological concepts
        - processes
        - terminology

        Question:
        {req.question_text}
        """
        else:
            query = f"""
        HSC Mathematics question involving:
        - derivatives
        - gradients
        - tangents

        Question:
        {req.question_text}
        """

        docs = retrieve_similar_solutions(query, req.subject, k=15)

        print("\n🔎 RETRIEVED SOLUTIONS FOR FEEDBACK:\n", docs)


        # ==============================
        # 3. Filter relevant docs
        # ==============================
        filtered_docs = []

        for d in docs:
            text = d.page_content.lower()

            if any(k in text for k in ["derivative", "tangent", "gradient"]):
                filtered_docs.append(d)

        if not filtered_docs:
            filtered_docs = docs[:5]  # fallback

        docs = filtered_docs


        # ==============================
        # 4. Build criteria context
        # ==============================
        criteria_context = json.dumps([
            {
                "criteria": d.metadata.get("criteria"),
                "sample_answer": d.page_content
            }
            for d in docs
        ], indent=2)


        # ==============================
        # 5. 🔥 RUBRIC GENERATION (KEY FIX)
        # ==============================

        math_rubric_prompt = f"""
You are an HSC mathematics marker.

Create a marking rubric for the question below.

QUESTION:
{req.question_text}

REFERENCES:
{criteria_context}

RULES:

- Use the REFERENCES to guide mark allocation and structure
- Do NOT copy from the references

- Each part must use banded marking (e.g. 3, 2, 1)
- Award ONE level per part (not additive)
- Total marks must be consistent with similar questions
- Prefer conservative mark allocation 
- Simple parts should have fewer marks

MULTIPLE CHOICE:
- If options A, B, C, D are present, it is 1 mark only
- No banded marking, no partial marks

STYLE:

- Each criterion is ONE short sentence
- Highest mark may use "Correct solution"
- Lower marks must describe specific partial progress
- Do NOT use generic phrases like "Correct method" or "Attempts solution"
- Do NOT include final answers
- No brackets or colons

LATEX:

- Use only if needed
- Wrap in \\( ... \\)
- Use f^{{\\prime}}(x), not f'(x)

Return STRICT JSON:

{{
  "rubric": [
    {{
      "part": "a",
      "criteria": [
        {{"criterion": "string", "marks": int}}
      ]
    }}
  ],
  "total_marks": int
}}
"""


        biology_rubric_prompt = f"""
        You are an expert NSW HSC Biology marker.

        Create a marking rubric for the question.

        QUESTION:
        {req.question_text}

        REFERENCES:
        {criteria_context}

        CRITICAL RULES:
        - Use HSC Biology marking style
        - Mark based on key biological concepts, not steps
        - Criteria must be progressive (banded marking)
        - Each level reflects depth of understanding
        - Use descending marks (e.g. 3, 2, 1)
        - DO NOT split into tiny steps

        MULTIPLE CHOICE RULE (OVERRIDES ALL OTHER RULES):
        - A question is considered multiple choice if it presents a list of answer options (e.g. A, B, C, D)
        - If the question is multiple choice (single correct option), it must be worth EXACTLY 1 mark
        - Do NOT apply banded marking to multiple choice questions
        - Do NOT create multiple criteria levels for multiple choice
        - The rubric for a multiple choice question should contain only ONE criterion:
        • Correct answer selected → 1 mark
        - No partial marks are to be awarded for multiple choice questions

        - This rule takes precedence over all other mark allocation rules

        MARK ALLOCATION RULES (VERY IMPORTANT):

        - Use the REFERENCES to guide how marks are distributed across parts
        - Identify the total marks and per-part marks from similar questions in the REFERENCES
        - The total marks for this question should be consistent with similar questions

        - Do NOT inflate marks beyond what is typical in the REFERENCES for specic question verbs (e.g. explain, analyse, evaluate)
        - Prefer slightly lower mark allocations rather than higher ones

        STYLE:
        - Use short, content-based criteria
        - Focus on:
        • accuracy of biological concepts
        • use of correct terminology
        • completeness of explanation

        Return STRICT JSON:

        {{
        "rubric": [
            {{
            "part": "a",
            "criteria": [
                {{"criterion": "Detailed and accurate explanation using correct terminology", "marks": 3}},
                {{"criterion": "Basic explanation with some correct terminology", "marks": 2}},
                {{"criterion": "Limited or partial understanding", "marks": 1}}
            ]
            }}
        ],
        "total_marks": int
        }}
    """


        if req.subject == "Biology":
            rubric_prompt = biology_rubric_prompt
        else:
            rubric_prompt = math_rubric_prompt


        rubric_response = client.responses.create(
            model="gpt-5.2",
            temperature=0.1,
            input=[{
                "role": "user",
                "content": [{"type": "input_text", "text": rubric_prompt}]
            }]
        )

        rubric_text = rubric_response.output_text.strip()

        print("\n📊 GENERATED RUBRIC:\n", rubric_text)

        # try:
        #     rubric_json = json.loads(rubric_text)
        # except:
        #     raise HTTPException(status_code=500, detail="Invalid rubric JSON")


        # ==============================
        # 6. 🔥 MARK USING RUBRIC
        # ==============================

        math_marking_prompt = f"""
        You are an HSC mathematics marker.

        QUESTION:
        {req.question_text}

        STUDENT SOLUTION:
        {student_solution}

        MARKING RUBRIC:
        {rubric_text}

        Mark the student's solution.

        CRITICAL RULES:
        - Use banded marking within each part (award ONE level only)
        - Use latex formatting for mathematical expressions in feedback
        - Output STRICT valid JSON
        - Do NOT combine criteria within a part
        - Output must follow a table-style structure
        - Use short, formal HSC-style comments
        - No emojis, no unnecessary wording

        For each part:
        - Select the appropriate criterion level
        - Award marks accordingly
        - Provide a short comment explaining correctness or error

        LATEX RULES (STRICT):

- Use standard LaTeX for all mathematical expressions (no restriction on commands)
- Wrap ALL mathematical expressions in \( ... \)

FORMAT RULE:
- Write LaTeX naturally (e.g. \frac{{x}}{{y}}, \ln x, e^{{2x}})
- Do NOT manually escape backslashes

JSON SAFETY RULE (CRITICAL):
- The output MUST be valid JSON parsable by Python json.loads()
- ALL backslashes in the final JSON string MUST be escaped as \\\\
- This means every LaTeX backslash must appear as \\\\ in the JSON output

EXAMPLES:
- Correct: "\\\\frac{{x}}{{y}}"
- Correct: "\\\\ln x"
- Correct: "\\\\(x^2\\\\)"
- Incorrect: "\frac{{x}}{{y}}"
- Incorrect: "\(x^2\)"

ADDITIONAL RULES:
- Do NOT produce invalid escape sequences such as \f, \l, \s
- Do NOT include raw LaTeX outside of JSON strings
- Do NOT include markdown, code blocks, or extra formatting

        - If backslashes are not escaped, the output is INVALID

        {{
        "marks_awarded": int,
        "total_marks": int,
        "marking_table": [
            {{
            "part": "a",
            "criterion": "Short criterion label",
            "marks_awarded": int,
            "max_marks": int,
            "comment": "Short explanation"
            }}
        ],
        "summary": "Brief overall judgement",
        "improvements": [
            "Short improvement",
            "Short improvement"
        ]
        }}
        """

        biology_marking_prompt = f"""
        You are an expert NSW HSC Biology marker.

        QUESTION:
        {req.question_text}

        STUDENT RESPONSE:
        {student_solution}

        MARKING RUBRIC:
        {rubric_text}

        Mark the student's response.

        CRITICAL RULES:
        - Use banded marking (ONE level per part)
        - Focus on biological understanding, not steps
        - Do NOT combine criteria within a part
        - Output must follow a table-style structure
        - Evaluate:
        • correctness of concepts
        • use of biological terminology
        • clarity of explanation
        - Penalise:
        • vague language
        • missing key ideas
        • incorrect terminology

        STYLE:
        - Use short HSC-style comments
        - No long explanations
        - No maths-style working
        - No LaTeX needed (plain text only)
        - Be concise and direct

        Return STRICT JSON:

     {{
    "marks_awarded": int,
    "total_marks": int,
    "marking_table": [
        {{
            "part": "a",
            "criterion": "Short label",
            "marks_awarded": int,
            "max_marks": int,
            "comment": "Short biology-specific comment"
        }}
    ],
    "summary": "Brief overall judgement",
    "improvements": [
        "Use more precise biological terminology",
        "Include missing key concept",
        "Improve explanation clarity"
    ]
}}
        """

        if req.subject == "Biology":
            rubric_prompt = biology_rubric_prompt
            marking_prompt = biology_marking_prompt
        else:
            rubric_prompt = math_rubric_prompt
            marking_prompt = math_marking_prompt

        response = client.responses.create(
            model="gpt-5.2",
            temperature=0.1,
            input=[
                {
                    "role": "user",
                    "content": [{"type": "input_text", "text": marking_prompt}]
                }
            ]
        )

        result_text = response.output_text.strip()

        print("\n🧾 FINAL MARKING OUTPUT:\n", result_text)

        try:
            result_json = json.loads(result_text)
        except:
            raise HTTPException(status_code=500, detail="Invalid marking JSON")

        return {
            "feedback": result_json
        }


    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"error": str(e)}


if __name__ == "__main__":
    # Get the advanced vectorstore
    advanced_vs = vectorstores.get("Mathematics Standard")

    if advanced_vs is None:
        print("No vectorstore found for Mathematics Advanced")
    else:
        print("Mathematics Advanced Vectorstore:")
        print(f"Number of documents: {len(advanced_vs.docstore._dict)}")

        # Optionally print a few docs
        for i, (doc_id, doc) in enumerate(advanced_vs.docstore._dict.items()):
            print(f"\nDoc {i+1} (ID={doc_id}):")
            print(f"  Question ID: {doc.metadata.get('question_id')}")
            print(f"  Topics: {doc.metadata.get('topics')}")
            print(f"  Preview: {doc.page_content[:100]}...")  # first 100 chars

            if i >= 4:  # stop after 5 docs
                break
    
    # Get the Mathematics Advanced solutions vectorstore
    solutions_vs = solution_vectorstores.get("Mathematics Advanced")

    if solutions_vs is None:
        print("No solutions vectorstore found for Mathematics Advanced")
    else:
        print("Mathematics Advanced Solutions Vectorstore:")
        print(f"Number of documents: {len(solutions_vs.docstore._dict)}")

        # Print a few sample documents
        for i, (doc_id, doc) in enumerate(solutions_vs.docstore._dict.items()):
            print(f"\nSolution Doc {i+1} (Internal ID={doc_id}):")
            print(f"  Question ID: {doc.metadata.get('question_id')}")
            print(f"  Solution ID: {doc.metadata.get('solution_id')}")
            print(f"  Criteria: {doc.metadata.get('criteria')}")
            print(f"  Diagram Description: {doc.metadata.get('diagram')}")
            print(f"\n  Content Preview:\n{doc.page_content[:300]}...")

            if i >= 4:  # stop after 5 docs
                break