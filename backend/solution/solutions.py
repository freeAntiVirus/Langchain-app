import os
import base64
import json
import random
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()  # loads variables from .env

# ---- CONFIG ----
ROOT_DIRECTORY = "./"  # folder containing 2020, 2021, etc.
OUTPUT_FILE = "solutions_output.json"

client = OpenAI()


def generate_unique_solution_id():
    """
    Generates a unique ID using datetime + random number
    """
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    random_part = random.randint(1000, 9999)
    return f"{timestamp}_{random_part}"

def extract_solution(image_path):
    """
    Sends image to OpenAI and extracts solution + criteria + diagram description
    """
    with open(image_path, "rb") as f:
        image_base64 = base64.b64encode(f.read()).decode()

    response = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """
Extract the worked solution from this image.

Return STRICT JSON in this format:
{
 "sample_answer": "full worked solution written entirely in LaTeX as a single string",
 "criteria": "marking criteria as a single string",
 "diagram_description": "detailed textual description of the diagram if one exists, otherwise empty string"
}

Rules:
- Preserve the solution exactly as written.
- Do NOT correct mistakes.
- Convert all mathematical expressions into valid LaTeX.
- Use proper LaTeX formatting (fractions, powers, roots, aligned equations where appropriate).
- Do NOT wrap the output in markdown code blocks.
- sample_answer must be a single continuous LaTeX string.
- criteria should describe how the solution would be marked.
- If a diagram exists:
    - Describe all labeled points
    - Shapes and geometry
    - Relative positions
    - Given lengths/angles
    - Arrows or direction indicators
    - Any graph axes, scales, intercepts
    - Enough detail so it can be reconstructed programmatically later.
- If no diagram exists, return "" for diagram_description.
- Do not include anything outside the JSON.
                        """
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}"
                        }
                    }
                ]
            }
        ],
        max_tokens=1800
    )

    return json.loads(response.choices[0].message.content)

def process_directory(root_dir):
    """
    Walk through directory structure and process all image files
    """
    all_results = []

    for year_folder in os.listdir(root_dir):
        year_path = os.path.join(root_dir, year_folder)

        if os.path.isdir(year_path):
            for filename in os.listdir(year_path):

                if filename.lower().endswith((".png", ".jpg", ".jpeg")):

                    file_path = os.path.join(year_path, filename)

                    print(f"Processing: {file_path}")

                    extracted = extract_solution(file_path)

                    question_id = os.path.splitext(filename)[0]

                    result_object = {
                        "QuestionId": question_id,
                        "SolutionId": generate_unique_solution_id(),
                        "SampleAnswer": extracted["sample_answer"],
                        "Criteria": extracted["criteria"],
                        "DiagramDescription": extracted.get("diagram_description", "")
                    }

                    all_results.append(result_object)

    return all_results


if __name__ == "__main__":

    results = process_directory(ROOT_DIRECTORY)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print("\n--- ALL SOLUTIONS SAVED ---\n")
    print(f"Saved to {OUTPUT_FILE}")