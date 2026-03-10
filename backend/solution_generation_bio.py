import os
import base64
import json
import webbrowser
from openai import OpenAI
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

load_dotenv()

# ---- CONFIG ----
IMAGE_PATH = "question.png"
SOLUTIONS_JSON_PATH = "solution/solutions_output.json"
MODEL_NAME = "gpt-5.2"

client = OpenAI()

VECTORSTORE_PATH = "solutions/biology"

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


# ---- LOAD CONTEXT SOLUTIONS ----
def load_solutions_context(json_path: str):
    with open(json_path, "r") as f:
        data = json.load(f)

    return json.dumps(data, indent=2)


def extract_question_text(image_base64):

    prompt = "Extract the exact question text from this image."

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

    return response.output_text.strip()

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

# ---- GENERATE SOLUTION ----
def generate_solution(image_path: str, solutions_json_path: str):

    image_base64 = encode_image(image_path)

    # Extract question text
    question_text = extract_question_text(image_base64)

    print("\n🧠 Extracted Question:\n")
    print(question_text)

    # Retrieve similar solutions
    retrieve_similar_solutions(question_text)

    solutions_context = load_solutions_context(solutions_json_path)

    system_prompt = """
You are an NSW HSC Biology exam marker.

Your task is to generate answers in the SAME style as official HSC sample solutions.

Rules:
• Match the wording and structure used in the sample answers.
• Use concise biological terminology.

Write answers the same way HSC marking guidelines present solutions.

Return JSON only with:
{
  "generated_solution": "answer written in HSC sample answer style",
  "final_answer": "concise final answer"
}
"""

    user_prompt = f"""
Below are official HSC sample solutions and marking criteria.

Study their style carefully.

Then write the solution to the question in the image using the SAME:
• structure
• wording style
• level of detail

Reference answers:

{solutions_context}

Generate the solution in the same style.

Return JSON only.
"""

    response = client.responses.create(
        model=MODEL_NAME,
        temperature=0.2,
        input=[
            {
                "role": "system",
                "content": [
                    {"type": "input_text", "text": system_prompt}
                ]
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


# ---- RENDER TO HTML (MathJax) ----
def render_to_html(solution_latex: str, output_name="generated_solution"):

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">

<script>
window.MathJax = {{
  tex: {{
    inlineMath: [['\\\\(','\\\\)']],
    displayMath: [['\\\\[','\\\\]']]
  }}
}};
</script>

<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>

<style>
body {{
    font-family: Arial, sans-serif;
    margin: 40px;
    line-height: 1.6;
}}

.solution {{
    max-width: 800px;
}}
</style>
</head>

<body>

<h2>Generated Solution</h2>

<div class="solution">
{solution_latex}
</div>

</body>
</html>
"""

    html_filename = f"{output_name}.html"

    with open(html_filename, "w") as f:
        f.write(html_content)

    print(f"\nHTML preview generated: {html_filename}")

    webbrowser.open(html_filename)

def render_to_tex(solution_latex: str, filename="generated_solution.tex"):

    tex_content = f"""
\\documentclass{{article}}
\\usepackage{{amsmath}}
\\usepackage{{amssymb}}

\\begin{{document}}

\\section*{{Generated Solution}}

{solution_latex}

\\end{{document}}
"""

    with open(filename, "w") as f:
        f.write(tex_content)

    print(f"TeX file generated: {filename}")

# ---- MAIN ----
if __name__ == "__main__":

    result_text = generate_solution(IMAGE_PATH, SOLUTIONS_JSON_PATH)

    try:
        result = json.loads(result_text)
    except json.JSONDecodeError:
        print("Model did not return valid JSON. Raw output:")
        print(result_text)
        raise

    print("\n--- GENERATED SOLUTION JSON ---\n")
    print(json.dumps(result, indent=2))

    render_to_html(result["generated_solution"])
    render_to_tex(result["generated_solution"])