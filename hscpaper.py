import os
import sys
import pdfplumber
from dotenv import load_dotenv

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.documents import Document
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter

load_dotenv()

def load_topics(filepath="topics.txt"):
    with open(filepath, "r") as f:
        return f.read()

def embed_topics(topic_text):
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    topic_docs = splitter.create_documents([topic_text])
    vectorstore = FAISS.from_documents(topic_docs, OpenAIEmbeddings())
    return vectorstore

def extract_pdf_text(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text.strip()

def classify_questions_and_parts(pdf_text, retriever):
    context_docs = retriever.get_relevant_documents("Classify HSC Maths questions")
    context = "\n".join(doc.page_content for doc in context_docs)

    prompt = ChatPromptTemplate.from_messages([
        ("system", "You are an expert HSC Mathematics teacher."),
        ("human",
         "Using the topic list below and the HSC paper content, do the following:\n\n"
         "1. Detect each question and sub-part (like 1(a), 1(b), etc) from the provided paper text.\n"
         "2. Classify each part into one or more topic codes.\n"
         "3. Output the result in this format:\n"
         "1. → [Graphing Techniques, Working with functions]\n"
         "2. → [Integral Calculus]\n"
         "...\n\n"
         "If a part could belong to more than one topic, list them all. If it is ambiguous, make the best guess and say why.\n\n"
         "TOPICS:\n{context}\n\n"
         "HSC PAPER TEXT:\n{question_text}"
         )
    ])

    model = ChatOpenAI(model="gpt-4o", temperature=0)
    messages = prompt.format_messages(context=context, question_text=pdf_text)
    response = model.invoke(messages)
    return response.content.strip()

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 hscpaper.py <your-hsc-paper.pdf>")
        return

    pdf_path = sys.argv[1]
    if not os.path.exists(pdf_path):
        print(f"PDF not found: {pdf_path}")
        return

    topic_text = load_topics()
    vectorstore = embed_topics(topic_text)
    retriever = vectorstore.as_retriever()

    pdf_text = extract_pdf_text(pdf_path)
    output = classify_questions_and_parts(pdf_text, retriever)

    print("\n✅ CLASSIFICATION RESULT:\n")
    print(output)

if __name__ == "__main__":
    main()
