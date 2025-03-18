import os
import pdfplumber
import asyncio
from dotenv import load_dotenv

load_dotenv()

import openai
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.chains import create_retrieval_chain
from langchain_core.messages import HumanMessage, AIMessage
from langchain_core.prompts import MessagesPlaceholder
from langchain.chains.history_aware_retriever import create_history_aware_retriever
from langchain_core.documents import Document


# Function to extract text from a PDF file
def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            extracted_text = page.extract_text()
            if extracted_text:
                text += extracted_text + "\n"
    return text


# Function to split the extracted text into smaller chunks
def split_documents(text):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=400,
        chunk_overlap=20
    )
    chunks = splitter.split_text(text)
    docs = [Document(page_content=chunk) for chunk in chunks]
    return docs


# Function to create a vector store database using FAISS and OpenAI embeddings
async def create_db(docs):
    embedding = OpenAIEmbeddings()
    vectorStore = await FAISS.afrom_documents(docs, embedding=embedding)
    return vectorStore


# Function to create a retrieval chain for answering questions based on the vector store
async def create_chain(vectorStore, context):
    model = ChatOpenAI(
        model="gpt-4o",
        temperature=0.4
    )

    # Define the prompt for extracting question numbers related to a topic
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Classify the question numbers based on the predefined topics from the provided context."),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        ("human", "Here is the context:\n{context}")
    ])

    # Create a chain that processes the documents
    chain = create_stuff_documents_chain(
        llm=model,
        prompt=prompt,
        document_variable_name="context"  # Ensure context is properly mapped
    )

    # Create a retriever using the vector store
    retriever = vectorStore.as_retriever(search_kwargs={"k": 3})

    # Define the prompt for the history-aware retriever
    retriever_prompt = ChatPromptTemplate.from_messages([
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        ("human", "Generate a search query to look up in order to get information relevant to the conversation")
    ])

    # Create a history-aware retriever
    history_aware_retriever = create_history_aware_retriever(
        llm=model,
        retriever=retriever,
        prompt=retriever_prompt
    )

    # Create a retrieval chain using the history-aware retriever
    retrieval_chain = create_retrieval_chain(
        history_aware_retriever,
        chain
    )

    return retrieval_chain


# Function to process the chat and get the response based on the question and chat history
async def process_chat(chain, question, chat_history, context):
    response = chain.invoke({
        "input": question,
        "chat_history": chat_history,
        "context": context
    })
    return response["answer"]


# Function to classify questions into topics with progress updates
async def classify_questions(chain, questions, chat_history, context):
    classifications = []
    total_questions = len(questions)
    for i, question in enumerate(questions):
        print(f"Classifying question {i + 1} of {total_questions}...")
        response = await process_chat(chain, f"Classify the question: {question}", chat_history, context)
        classifications.append((question, response))
    return classifications


# Main function to run the entire process
async def main():
    pdf_path = "/Users/kifayashehadeh/Desktop/2020-hsc-mathematics-standard-2.pdf"  # Replace with your actual PDF path
    context_paths = [
        "/Users/kifayashehadeh/Downloads/context.pdf",
    ]

    # Step 1: Extract text from the PDF
    text = extract_text_from_pdf(pdf_path)

    # Step 2: Extract text from context documents
    context_texts = [extract_text_from_pdf(path) for path in context_paths]
    context = "\n".join(context_texts)

    # Step 3: Split the extracted text into smaller chunks
    docs = split_documents(text)

    # Step 4: Create a vector store database
    vectorStore = await create_db(docs)

    # Step 5: Create a retrieval chain with context
    chain = await create_chain(vectorStore, context)

    while True:
        # Step 6: Ask the user for the topic of interest
        topic = input("Enter the topics of interest (or type 'exit' to quit): ")
        if topic.lower() == 'exit':
            break

        chat_history = []

        # Step 7: Process the chat to get the response
        questions = text.split("\n")  # Assuming each question is on a new line
        classifications = await classify_questions(chain, questions, chat_history, context)

        for question, topics in classifications:
            print(f"Question: {question}\nTopics: {topics}\n")


# Run the main function
if __name__ == '__main__':
    asyncio.run(main())
