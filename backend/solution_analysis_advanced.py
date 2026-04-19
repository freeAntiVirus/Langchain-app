import os
import base64
import json
from openai import OpenAI
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

load_dotenv()

# ---- CONFIG ----
IMAGE_PATH = "question.png"
SOLUTIONS_JSON_PATH = "solution/papers/solutions_output.json"
MODEL_NAME = "gpt-5.2"

client = OpenAI()

VECTORSTORE_PATH = "solutions/advanced"

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

solution_vectorstore = FAISS.load_local(
    VECTORSTORE_PATH,
    embeddings,
    allow_dangerous_deserialization=True
)

# ---- HELPER: Encode image ----
def encode_image(image_path: str):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# ---- SAFE TEXT EXTRACTION FROM RESPONSE ----
def get_output_text(response):
    output_text = ""

    try:
        for item in response.output:
            for content in item.content:
                if hasattr(content, "text") and content.text:
                    output_text += content.text
    except Exception:
        pass

    return output_text.strip()


# ---- LOAD CONTEXT SOLUTIONS ----
def load_solutions_context(json_path: str):
    with open(json_path, "r") as f:
        data = json.load(f)
    return json.dumps(data, indent=2)


def retrieve_similar_solutions(question_text, k=5):

    retriever = solution_vectorstore.as_retriever(search_kwargs={"k": k})
    docs = retriever.invoke(question_text)

    print("\n🔎 Retrieved similar solutions:\n")

    for i, doc in enumerate(docs):
        print(f"\n--- Solution {i+1} ---")
        print("Question ID:", doc.metadata.get("question_id"))
        print("Solution ID:", doc.metadata.get("solution_id"))
        print("Criteria:", doc.metadata.get("criteria"))
        print("\nPreview:\n", doc.page_content[:300])

    return docs


# ---- EXTRACT QUESTION + STUDENT SOLUTION ----
def extract_student_solution(image_base64):

    prompt = """
Extract BOTH:
1. The question
2. The student's FULL working/solution

Return STRICT JSON ONLY:
{
  "question": "...",
  "student_solution": "..."
}
"""

    response = client.responses.create(
        model=MODEL_NAME,
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

    output_text = get_output_text(response)

    print("\n🧾 RAW EXTRACTION OUTPUT:\n", output_text)

    if not output_text:
        raise ValueError("❌ Model returned empty output")

    try:
        return json.loads(output_text)
    except json.JSONDecodeError:
        print("⚠️ JSON parsing failed. Attempting fix...")

        # Attempt simple cleanup
        cleaned = output_text.strip().strip("```json").strip("```")

        try:
            return json.loads(cleaned)
        except:
            raise ValueError("❌ Still invalid JSON:\n" + output_text)


# ---- ANALYSE SOLUTION ----
def analyse_solution(image_path: str, solutions_json_path: str):

    image_base64 = encode_image(image_path)

    extracted = extract_student_solution(image_base64)

    question_text = extracted["question"]
    student_solution = extracted["student_solution"]

    print("\n🧠 Extracted Question:\n", question_text)
    print("\n📝 Student Solution:\n", student_solution)

    docs = retrieve_similar_solutions(question_text)

    criteria_context = []
    for doc in docs:
        criteria_context.append({
            "criteria": doc.metadata.get("criteria"),
            "sample_answer": doc.page_content
        })

    criteria_context = json.dumps(criteria_context, indent=2)

    system_prompt = """
You are an expert HSC mathematics marker.

You MUST mark the student's solution using the provided marking criteria.

Rules:
• Award marks strictly based on criteria
• Identify missing steps
• Identify correct steps
• Provide constructive feedback
• Be consistent with HSC marking guidelines
• Do NOT generate a new solution unless needed for explanation

Marking Rules (CRITICAL):

Criteria within a part are NOT additive
They represent progressive marking bands
Award ONLY the highest valid mark within each part
Do NOT sum criteria within a part
Then sum marks across parts

Return STRICT JSON ONLY.
"""

    user_prompt = f"""
QUESTION:
{question_text}

STUDENT SOLUTION:
{student_solution}

MARKING REFERENCES:
{criteria_context}

Return STRICT JSON:

{{
  "marks_awarded": int,
  "total_marks": int,
  "criteria_breakdown": [
    {{
      "criterion": "...",
      "awarded": true/false,
      "comment": "..."
    }}
  ],
  "feedback_summary": "...",
  "improvements": ["...", "..."]
}}
"""

    response = client.responses.create(
        model=MODEL_NAME,
        temperature=0.1,
        input=[
            {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
            {"role": "user", "content": [{"type": "input_text", "text": user_prompt}]}
        ]
    )

    output_text = get_output_text(response)

    print("\n🧾 RAW MARKING OUTPUT:\n", output_text)

    if not output_text:
        raise ValueError("❌ Empty marking response")

    return output_text


# ---- MAIN ----
if __name__ == "__main__":

    result_text = analyse_solution(IMAGE_PATH, SOLUTIONS_JSON_PATH)

    try:
        result = json.loads(result_text)
    except json.JSONDecodeError:
        print("⚠️ Final JSON parsing failed. Raw output:\n")
        print(result_text)
        raise

    print("\n--- MARKING RESULT ---\n")
    print(json.dumps(result, indent=2))