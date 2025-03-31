import json
import os
import re
import pdfplumber
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.messages import AIMessage

load_dotenv()
app = FastAPI()

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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

# Extract text from PDF
def extract_pdf_text(file):
    text = ""
    with pdfplumber.open(file) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text.strip()

# Classify questions
def classify_questions(pdf_text):
    # context_docs = retriever.get_relevant_documents("Classify HSC Maths questions")
    # context = "\n".join(doc.page_content for doc in context_docs)
    
    retrieved_docs = retriever.get_relevant_documents("Classify HSC Maths questions")
    past_corrections = "\n".join(doc.page_content for doc in retrieved_docs)


    prompt = ChatPromptTemplate.from_template(
        """You are an expert HSC Mathematics teacher.

    Your job is to classify each question and sub-part (e.g. 1, 2(a)) into one or more topic codes.

    ❗ VERY IMPORTANT:
    - Use only topic names from the official list below — exactly as written.
    - Do NOT invent new topics, abbreviate, paraphrase, or shorten names.
    - Do NOT say "Financial Maths" — use "MA-M1: Modelling Financial Situations".
    - Do NOT say "Probability" — use "MA-S1: Probability and Discrete Probability Distributions".
    - Make sure to include a colon (:) after topic code.
    - If unsure, choose the closest topic from the official list — but never make one up.

    🔁 Previous corrections may help inform your decisions:
    {past_corrections}

    📋 OFFICIAL TOPIC LIST (use exact names only):
    {topics}

    📝 Format:
    [
    {{ "question": "1(a)", "topics": ["MA-F1: Working with functions"] }},
    ...
    ]

    📄 HSC PAPER TEXT:
    {question_text}
    """
    )


    model = ChatOpenAI(model="gpt-4o", temperature=0)
    messages = prompt.format_messages(
        past_corrections=past_corrections,
        topics=topic_text.strip(),
        question_text=pdf_text
    )

    response = model.invoke(messages)

 # Extract response content safely
    content = getattr(response, "content", "") if isinstance(response, AIMessage) else str(response)

    if not content:
        raise ValueError("❌ GPT response was empty.")

    # Extract first JSON array (starts with [ ends with ])
    match = re.search(r"\[\s*{.*?}\s*]", content, re.DOTALL)
    if not match:
        print("❌ Could not find JSON array in response.")
        print("Full response:\n", content)
        raise ValueError("No valid JSON array found in model output.")

    cleaned = match.group(0)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        print("❌ Failed to parse JSON array.")
        print("Extracted content:\n", cleaned)
        raise e
    
@app.post("/classify/")
async def classify(file: UploadFile = File(...)):
    file_path = f"temp_{file.filename}"
    with open(file_path, "wb") as f:
        f.write(await file.read())

    try:
        pdf_text = extract_pdf_text(file_path)
        result = classify_questions(pdf_text)
        return {"result": result}
    finally:
        os.remove(file_path)

class Correction(BaseModel):
    question: str
    corrected_topics: List[str]

@app.post("/submit_corrections/")
async def submit_corrections(corrections: List[Correction]):
    new_docs = []
    for correction in corrections:
        content = f"{correction.question} → {', '.join(correction.corrected_topics)}"
        new_docs.append(content)

    docs = splitter.create_documents(new_docs)
    vectorstore.add_documents(docs)
    vectorstore.save_local(VECTORSTORE_PATH)
    return {"message": "Corrections saved."}
