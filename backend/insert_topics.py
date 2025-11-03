from pymongo import MongoClient
from dotenv import load_dotenv
import os

# Load environment variables from .env
load_dotenv()

# Connect to MongoDB
client = MongoClient(os.getenv("MONGO_URI"))
db = client["hschub"]

# Define topics with name format: "TopicId: Topic Name (Year)"
topics_data = [
    # ---------------- Mathematics Advanced ----------------
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
    {"TopicId": "MA-M1", "name": "MA-M1: Modelling Financial Situations (Year 12)", "subject": "Mathematics Advanced"},

    # ---------------- Mathematics Standard (Year 11) ----------------
    {"TopicId": "MS-M1", "name": "MS-M1: Applications of Measurement (Year 11)", "subject": "Mathematics Standard"},
    {"TopicId": "M1.1", "name": "M1.1: Practicalities of Measurement (Year 11)", "subject": "Mathematics Standard"},
    {"TopicId": "M1.2", "name": "M1.2: Perimeter, Area and Volume (Year 11)", "subject": "Mathematics Standard"},
    {"TopicId": "M1.3", "name": "M1.3: Units of Energy and Mass (Year 11)", "subject": "Mathematics Standard"},

    {"TopicId": "MS-M2", "name": "MS-M2: Working with Time (Year 11)", "subject": "Mathematics Standard"},

    {"TopicId": "MS-F1", "name": "MS-F1: Money Matters (Year 11)", "subject": "Mathematics Standard"},
    {"TopicId": "F1.1", "name": "F1.1: Interest and Depreciation (Year 11)", "subject": "Mathematics Standard"},
    {"TopicId": "F1.2", "name": "F1.2: Earning and Managing Money (Year 11)", "subject": "Mathematics Standard"},
    {"TopicId": "F1.3", "name": "F1.3: Budgeting and Household Expenses (Year 11)", "subject": "Mathematics Standard"},

    {"TopicId": "MS-A1", "name": "MS-A1: Formulae and Equations (Year 11)", "subject": "Mathematics Standard"},
    {"TopicId": "MS-A2", "name": "MS-A2: Linear Relationships (Year 11)", "subject": "Mathematics Standard"},

    {"TopicId": "MS-S1", "name": "MS-S1: Data Analysis (Year 11)", "subject": "Mathematics Standard"},
    {"TopicId": "S1.1", "name": "S1.1: Classifying and Representing Data (Year 11)", "subject": "Mathematics Standard"},
    {"TopicId": "S1.2", "name": "S1.2: Summary Statistics (Year 11)", "subject": "Mathematics Standard"},

    {"TopicId": "MS-S2", "name": "MS-S2: Relative Frequency and Probability (Year 11)", "subject": "Mathematics Standard"},

    # ---------------- Mathematics Standard (Year 12) ----------------
    {"TopicId": "MS-A4", "name": "MS-A4: Types of Relationships (Year 12)", "subject": "Mathematics Standard"},
    {"TopicId": "A4.1", "name": "A4.1: Simultaneous Linear Equations (Year 12)", "subject": "Mathematics Standard"},
    {"TopicId": "A4.2", "name": "A4.2: Non-linear Relationships (Year 12)", "subject": "Mathematics Standard"},

    {"TopicId": "MS-F4", "name": "MS-F4: Investments and Loans (Year 12)", "subject": "Mathematics Standard"},
    {"TopicId": "F4.1", "name": "F4.1: Investments (Year 12)", "subject": "Mathematics Standard"},
    {"TopicId": "F4.2", "name": "F4.2: Depreciation and Loans (Year 12)", "subject": "Mathematics Standard"},

    {"TopicId": "MS-F5", "name": "MS-F5: Annuities (Year 12)", "subject": "Mathematics Standard"},

    {"TopicId": "MS-M6", "name": "MS-M6: Non-right-angled Trigonometry (Year 12)", "subject": "Mathematics Standard"},
    {"TopicId": "MS-M7", "name": "MS-M7: Rates and Ratios (Year 12)", "subject": "Mathematics Standard"},

    {"TopicId": "MS-S4", "name": "MS-S4: Bivariate Data Analysis (Year 12)", "subject": "Mathematics Standard"},
    {"TopicId": "MS-S5", "name": "MS-S5: The Normal Distribution (Year 12)", "subject": "Mathematics Standard"},

    {"TopicId": "MS-N2", "name": "MS-N2: Network Concepts (Year 12)", "subject": "Mathematics Standard"},
    {"TopicId": "N2.1", "name": "N2.1: Networks (Year 12)", "subject": "Mathematics Standard"},
    {"TopicId": "N2.2", "name": "N2.2: Shortest Paths (Year 12)", "subject": "Mathematics Standard"},

    {"TopicId": "MS-N3", "name": "MS-N3: Critical Path Analysis (Year 12)", "subject": "Mathematics Standard"},
    

    # ---------------- Biology (Year 11) ----------------
    { "TopicId": "BIO-M1.1", "name": "BIO-M1.1: Cell Structure (Year 11)", "subject": "Biology" },
    { "TopicId": "BIO-M1.1", "name": "BIO-M1.2: Cell Function (Year 11)", "subject": "Biology" },

    { "TopicId": "BIO-M2.1", "name": "BIO-M2.1: Organisation of Cells (Year 11)", "subject": "Biology" },
    { "TopicId": "BIO-M2.2", "name": "BIO-M2.1: Nutrient and Gas Requirements (Year 11)", "subject": "Biology" },
    { "TopicId": "BIO-M2.3", "name": "BIO-M2.3: Transport (Year 11)", "subject": "Biology" },

    { "TopicId": "BIO-M3.1", "name": "BIO-M3.1: Effects of the Environment on Organisms (Year 11)", "subject": "Biology" },
    { "TopicId": "BIO-M3.2", "name": "BIO-M3.2: Adaptations (Year 11)", "subject": "Biology" },
    { "TopicId": "BIO-M3.3", "name": "BIO-M3.3: Theory of Evolution by Natural Selection (Year 11)", "subject": "Biology" },
    { "TopicId": "BIO-M3.4", "name": "BIO-M3.4: Evolution – the Evidence (Year 11)", "subject": "Biology" },

    { "TopicId": "BIO-M4.1", "name": "BIO-M4.1: Population Dynamics (Year 11)", "subject": "Biology" },
    { "TopicId": "BIO-M4.2", "name": "BIO-M4.2: Past Ecosystems (Year 11)", "subject": "Biology" },
    { "TopicId": "BIO-M4.3", "name": "BIO-M4.3: Future Ecosystems (Year 11)", "subject": "Biology" },
    { "TopicId": "BIO-M4.4", "name": "BIO-M4.4: Human Impact (Year 11)", "subject": "Biology" },

    # ---------------- Biology (Year 12) ----------------
    { "TopicId": "BIO-M5.1", "name": "BIO-M5.1: Reproduction (Year 12)", "subject": "Biology" },
    { "TopicId": "BIO-M5.2", "name": "BIO-M5.2: Cell Replication (Year 12)", "subject": "Biology" },
    { "TopicId": "BIO-M5.3", "name": "BIO-M5.3: DNA and Polypeptide Synthesis (Year 12)", "subject": "Biology" },
    { "TopicId": "BIO-M5.4", "name": "BIO-M5.4: Genetic Variation (Year 12)", "subject": "Biology" },
    { "TopicId": "BIO-M5.5", "name": "BIO-M5.5: Inheritance Patterns in a Population (Year 12)", "subject": "Biology" },

    { "TopicId": "BIO-M6.1", "name": "BIO-M6.1: Mutation (Year 12)", "subject": "Biology" },
    { "TopicId": "BIO-M6.2", "name": "BIO-M6.2: Biotechnology (Year 12)", "subject": "Biology" },
    { "TopicId": "BIO-M6.3", "name": "BIO-M6.3: Genetic Technologies (Year 12)", "subject": "Biology" },

    { "TopicId": "BIO-M7.1", "name": "BIO-M7.1: Causes of Infectious Disease (Year 12)", "subject": "Biology" },
    { "TopicId": "BIO-M7.2", "name": "BIO-M7.2: Responses to Pathogens (Year 12)", "subject": "Biology" },
    { "TopicId": "BIO-M7.3", "name": "BIO-M7.3: Immunity (Year 12)", "subject": "Biology" },
    { "TopicId": "BIO-M7.4", "name": "BIO-M7.4: Prevention, Treatment and Control (Year 12)", "subject": "Biology" },

    { "TopicId": "BIO-M8.1", "name": "BIO-M8.1: Homeostasis (Year 12)", "subject": "Biology" },
    { "TopicId": "BIO-M8.2", "name": "BIO-M8.2: Causes and Effects (Year 12)", "subject": "Biology" },
    { "TopicId": "BIO-M8.3", "name": "BIO-M8.3: Epidemiology (Year 12)", "subject": "Biology" },
    { "TopicId": "BIO-M8.4", "name": "BIO-M8.4: Prevention (Year 12)", "subject": "Biology" },
    { "TopicId": "BIO-M8.5", "name": "BIO-M8.5: Technologies and Disorders (Year 12)", "subject": "Biology" },

    # ---------------- Working Scientifically (Common to Y11 & Y12) ----------------
    { "TopicId": "BIO-WS1", "name": "BIO-WS1: Questioning and Predicting", "subject": "Biology", "outcomes": ["BIO11/12-1"], "description": "Develops and evaluates questions and hypotheses for scientific investigation." },
    { "TopicId": "BIO-WS2", "name": "BIO-WS2: Planning Investigations", "subject": "Biology", "outcomes": ["BIO11/12-2"], "description": "Designs and evaluates investigations to obtain primary and secondary data and information." },
    { "TopicId": "BIO-WS3", "name": "BIO-WS3: Conducting Investigations", "subject": "Biology", "outcomes": ["BIO11/12-3"], "description": "Conducts investigations to collect valid and reliable primary and secondary data and information." },
    { "TopicId": "BIO-WS4", "name": "BIO-WS4: Processing Data and Information", "subject": "Biology", "outcomes": ["BIO11/12-4"], "description": "Selects and processes appropriate qualitative and quantitative data and information using a range of appropriate media." },
    { "TopicId": "BIO-WS5", "name": "BIO-WS5: Analysing Data and Information", "subject": "Biology", "outcomes": ["BIO11/12-5"], "description": "Analyses and evaluates primary and secondary data and information." },
    { "TopicId": "BIO-WS6", "name": "BIO-WS6: Problem Solving", "subject": "Biology", "outcomes": ["BIO11/12-6"], "description": "Solves scientific problems using primary and secondary data, critical thinking skills and scientific processes." },
    { "TopicId": "BIO-WS7", "name": "BIO-WS7: Communicating", "subject": "Biology", "outcomes": ["BIO11/12-7"], "description": "Communicates scientific understanding using suitable language and terminology for a specific audience or purpose." }

]

# Reset and insert
db["topics"].delete_many({})
db["topics"].insert_many(topics_data)

print("Topics inserted")
