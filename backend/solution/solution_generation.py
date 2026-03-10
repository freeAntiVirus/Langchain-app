import os
import base64
import json
import subprocess
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ---- CONFIG ----
IMAGE_PATH = "question.png"
SOLUTIONS_JSON_PATH = "solutions_output.json"
MODEL_NAME = "gpt-5.2"

client = OpenAI()


# ---- HELPER: Encode image ----
def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


# ---- LOAD CONTEXT SOLUTIONS ----
def load_solutions_context(json_path: str) -> str:
    with open(json_path, "r") as f:
        data = json.load(f)

    return json.dumps(data, indent=2)


# ---- GENERATE SOLUTION ----
def generate_solution(image_path: str, solutions_json_path: str):

    image_base64 = encode_image(image_path)
    solutions_context = load_solutions_context(solutions_json_path)

    system_prompt = """
You are an expert mathematics exam marker.

You are given marking criteria and worked solutions for similar past questions.

These are NOT just examples — they define:
• The marking logic
• The required working steps
• The structure needed to earn marks
• The level of explanation expected

Your task is to:
1. Carefully analyse the Criteria section.
2. Identify the types of steps required to earn method marks.
3. Apply the same marking standards to the new question.
4. Explicitly show all working needed for full marks.
5. Do not skip intermediate steps.
6. If probabilities are required, show setup before simplifying.
7. Use any DiagramDescription information accurately.
8. Ensure the solution would receive FULL marks under similar marking rules.

Before finalizing internally check:
- Every criteria bullet point has been satisfied.

Output Rules:
- Return VALID JSON only.
- Include EXACTLY two keys:
    - "generated_solution": full worked solution written in LaTeX.
    - "final_answer": concise final answer only.
- No commentary outside JSON.
"""

    user_prompt = f"""
You are provided with marking criteria and sample answers from similar questions.

These define:
• How marks are awarded
• What working must be shown
• What earns method marks
• What earns accuracy marks

Here is the reference JSON:

{solutions_context}

Using the SAME marking standards:
- Follow the Criteria structure.
- Include all mark-worthy intermediate steps.
- Match the structure and clarity of the SampleAnswer.
- Use DiagramDescription if relevant.
- Ensure the answer would earn full marks under similar marking rules.

Now generate a complete worked solution for the question shown in the image.

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


# ---- RENDER TO LATEX PDF ----
def render_to_latex_pdf(solution_latex: str, output_name="generated_solution"):

    tex_content = f"""
\\documentclass{{article}}
\\usepackage{{amsmath}}
\\usepackage{{amssymb}}
\\usepackage{{geometry}}
\\geometry{{margin=1in}}

\\begin{{document}}

\\section*{{Generated Solution}}

{solution_latex}

\\end{{document}}
"""

    tex_filename = f"{output_name}.tex"

    with open(tex_filename, "w") as f:
        f.write(tex_content)

    print(f"\nLaTeX file written to {tex_filename}")

    try:
        subprocess.run(["pdflatex", tex_filename], check=True)
        print(f"PDF generated: {output_name}.pdf")
    except Exception:
        print("pdflatex not found. Install LaTeX or use HTML preview instead.")


# ---- RENDER TO HTML (MathJax) ----
def render_to_html(solution_latex: str, output_name="generated_solution"):

    html_content = f"""
<!DOCTYPE html>
<html>
<head>
<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"></script>
</head>
<body>
<h2>Generated Solution</h2>
<p>\\[
{solution_latex}
\\]</p>
</body>
</html>
"""

    html_filename = f"{output_name}.html"

    with open(html_filename, "w") as f:
        f.write(html_content)

    print(f"\nHTML preview generated: {html_filename}")
    print("Open this file in your browser to view rendered LaTeX.")


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

    render_to_latex_pdf(result["generated_solution"])
    render_to_html(result["generated_solution"])