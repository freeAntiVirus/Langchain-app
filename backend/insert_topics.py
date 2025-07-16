from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Connect to MongoDB
client = MongoClient(os.getenv("MONGO_URI"))
db = client["test_db"]

# Define topics with name format: "TopicId: Topic Name (Year)"
topics_data = [
    {"TopicId": "MA-C1", "name": "MA-C1: Introduction to Differentiation (Year 11)", "subject": "Mathematics Advanced"},
    {"TopicId": "MA-C2", "name": "MA-C2: Differential Calculus (Year 12)", "subject": "Mathematics Advanced"},
    {"TopicId": "MA-C3", "name": "MA-C3: Applications of Differentiation (Year 12)", "subject": "Mathematics Advanced"},
    {"TopicId": "MA-C4", "name": "MA-C4: Integral Calculus (Year 12)", "subject": "Mathematics Advanced"},
    {"TopicId": "MA-E1", "name": "MA-E1: Logarithms and Exponentials (Year 11)", "subject": "Mathematics Advanced"},
    {"TopicId": "MA-F1", "name": "MA-F1: Working with Functions (Year 11)", "subject": "Mathematics Advanced"},
    {"TopicId": "MA-F2", "name": "MA-F2: Graphing Techniques (Year 12)", "subject": "Mathematics Advanced"},
    {"TopicId": "MA-S1", "name": "MA-S1: Probability and Discrete Probability Distributions (Year 11)", "subject": "Mathematics Advanced"},
    {"TopicId": "MA-S2", "name": "MA-S2: Descriptive Statistics and Bivariate Data Analysis (Year 12)", "subject": "Mathematics Advanced"},
    {"TopicId": "MA-S3", "name": "MA-S3: Random Variables (Year 12)", "subject": "Mathematics Advanced"},
    {"TopicId": "MA-T1", "name": "MA-T1: Trigonometry and Measure of Angles (Year 11)", "subject": "Mathematics Advanced"},
    {"TopicId": "MA-T2", "name": "MA-T2: Trigonometric Functions and Identities (Year 11)", "subject": "Mathematics Advanced"},
    {"TopicId": "MA-T3", "name": "MA-T3: Trigonometric Functions and Graphs (Year 12)", "subject": "Mathematics Advanced"},
    {"TopicId": "MA-M1", "name": "MA-M1: Modelling Financial Situations (Year 12)", "subject": "Mathematics Advanced"}
]

# Reset and insert
db["topics"].delete_many({})
db["topics"].insert_many(topics_data)

print("Topics inserted")
