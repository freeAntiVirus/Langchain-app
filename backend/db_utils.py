
from typing import List, Dict, Any
import random

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
        
def fetch_questions_with_all_topics(db, topic_names: List[str], limit: int = 8) -> List[Dict[str, Any]]:
    """
    Mongo version of 'intersection query':
    1) Resolve topic_ids for all topic_names
    2) Pull classification docs for those topic_ids
    3) Build map QuestionId -> set(TopicId) (only counting requested topic_ids)
    4) Keep only QuestionIds that cover *all* requested topic_ids
    5) Fetch question docs for those ids; return up to 'limit'
    """
    if not topic_names:
        return []

    # 1) Resolve topic_ids
    topic_docs = list(db["topics"].find(
        {"name": {"$in": topic_names}},
        {"_id": 0, "TopicId": 1, "name": 1}
    ))
    if len(topic_docs) != len(topic_names):
        # Some topics not found -> return empty (caller handles)
        return []

    requested_topic_ids = {t["TopicId"] for t in topic_docs}

    # 2) Pull classification docs for *only* requested topic_ids
    classification_docs = list(db["classification"].find(
        {"TopicId": {"$in": list(requested_topic_ids)}},
        {"_id": 0, "TopicId": 1, "QuestionId": 1}
    ))

    # 3) Build QuestionId -> set(TopicId) covered (from requested set only)
    q_map = {}
    for doc in classification_docs:
        qid = doc["QuestionId"]
        tid = doc["TopicId"]
        if qid not in q_map:
            q_map[qid] = set()
        if tid in requested_topic_ids:
            q_map[qid].add(tid)

    # 4) Keep only qids that cover ALL requested topic_ids
    full_cover_qids = [qid for qid, tids in q_map.items() if tids >= requested_topic_ids]
    if not full_cover_qids:
        return []

    # Optional: randomize to get variety
    random.shuffle(full_cover_qids)

    # 5) Fetch question docs
    chosen_qids = full_cover_qids[:limit]
    questions = list(db["questions"].find(
        {"QuestionId": {"$in": chosen_qids}},
        {"_id": 0, "QuestionId": 1, "base64": 1, "text": 1, "latex": 1}
    ))
    return questions