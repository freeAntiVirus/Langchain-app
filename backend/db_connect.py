from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()


# Get MongoDB URI from .env
MONGO_URI = os.getenv("MONGO_URI")  # Format: mongodb+srv://user:pass@cluster0.mongodb.net/?retryWrites=true&w=majority


# Connect to MongoDB
client = MongoClient(MONGO_URI)

# Access database and collection
db = client["test_db"]
collection = db["questions"]

# Insert a question into the database
def insert_question(question_data):
    result = collection.insert_one(question_data)
    print("✅ Inserted with ID:", result.inserted_id)

# Get all questions
def get_all_questions():
    return list(collection.find())

# Example usage
if __name__ == "__main__":
    # Example question
    question = {
        "question_id": "Q004",
        "text": "What is the derivative of x²?",
        "topics": ["MA-C1: Calculus"]
    }

    insert_question(question)

    all_qs = get_all_questions()
    for q in all_qs:
        print(q)
