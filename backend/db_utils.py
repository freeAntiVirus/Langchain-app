
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

    # Remove any existing mappings for this question
    classifications_col.delete_many({"QuestionId": question_obj["id"]})

    # Insert fresh topic mappings
    for topic_id in topic_ids:
        classifications_col.insert_one({
            "QuestionId": question_obj["id"],
            "TopicId": topic_id
        })
        print(f"🔗 Mapped {question_obj['id']} to {topic_id}")