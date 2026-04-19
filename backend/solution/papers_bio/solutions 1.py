import os
import base64
import json
import random
from datetime import datetime
from openai import OpenAI
from dotenv import load_dotenv
from pdf2image import convert_from_path
import tempfile

load_dotenv()

# ---- CONFIG ----
ROOT_DIRECTORY = "./"
OUTPUT_FILE = "solutions_output.json"

client = OpenAI()


def generate_unique_solution_id():
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
    random_part = random.randint(1000, 9999)
    return f"{timestamp}_{random_part}"


def encode_image(image_path):
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def extract_solution(image_path):

    image_base64 = encode_image(image_path)

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
"criteria": [
{
"part": "question part label (e.g. (a), (b), (i), (ii))",
"criterion": "description of marking point",
"marks": int
}
],
"diagram_description": "detailed textual description of the diagram if one exists, otherwise empty string"
}

Rules:

Preserve the solution exactly as written.
Clearly label every part of the solution in the sample_answer (e.g. Question 21 (a), (b), (c)).
Every criterion MUST be explicitly linked to a specific question part using the "part" field.
Do NOT group criteria without a part — if unclear, infer the most likely part based on the solution structure.
Maintain the correct ordering of parts as they appear in the solution.
If multiple criteria belong to the same part, repeat the part label for each criterion.
Do NOT leave any criterion unassigned to a part.
Do NOT correct mistakes.
Convert all mathematical expressions into valid LaTeX.
Use proper LaTeX formatting.
Do NOT wrap the output in markdown.
sample_answer must be a single LaTeX string.
criteria must be a LIST of marking points.
Each criterion must include its mark value explicitly.
The sum of marks should reflect the total available marks.
If marks are implied, infer them conservatively.
If a diagram exists describe it in detail.
If no diagram exists return "".
Do not include anything outside JSON.

Part Labelling Rules (STRICT):

Every "part" MUST follow this exact format:
"(a)", "(b)", "(c)", "(i)", "(ii)" etc.
Do NOT include the question number in "part".
The question number must NOT appear in the "part" field.
If the solution includes "Question 26 (b)", extract only "(b)".
If only a question number is given (e.g. "Question 24" with no parts), use an empty string.
All parts must be consistent across the entire response.
Do NOT mix formats like "26 (b)", "Question 24", or "20".
                        """
                    },
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{image_base64}"}
                    }
                ]
            }
        ],
        max_tokens=1800
    )

    return json.loads(response.choices[0].message.content)


def process_pdf(pdf_path):

    results = []

    pages = convert_from_path(pdf_path, dpi=300)

    base_question_id = os.path.splitext(os.path.basename(pdf_path))[0]

    for page_index, page in enumerate(pages):

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as temp_file:

            temp_path = temp_file.name
            page.save(temp_path, "PNG")

            print(f"Processing PDF page: {pdf_path} page {page_index+1}")

            extracted = extract_solution(temp_path)

            # Convert page index to letter part (a, b, c, ...)
            part_letter = chr(ord('a') + page_index)

            sample_answer_with_part = f"({part_letter}) {extracted['sample_answer']}"

            result_object = {
                "QuestionId": base_question_id,
                "SolutionId": generate_unique_solution_id(),
                "SampleAnswer": sample_answer_with_part,
                "Criteria": extracted["criteria"],
                "DiagramDescription": extracted.get("diagram_description", "")
            }

            results.append(result_object)

        os.remove(temp_path)

    return results


def process_directory(root_dir):

    all_results = []

    for year_folder in os.listdir(root_dir):

        year_path = os.path.join(root_dir, year_folder)

        if os.path.isdir(year_path):

            for filename in os.listdir(year_path):

                file_path = os.path.join(year_path, filename)

                if filename.lower().endswith((".png", ".jpg", ".jpeg")):

                    print(f"Processing image: {file_path}")

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

                elif filename.lower().endswith(".pdf"):

                    print(f"Processing PDF: {file_path}")

                    pdf_results = process_pdf(file_path)

                    all_results.extend(pdf_results)

    return all_results


if __name__ == "__main__":

    results = process_directory(ROOT_DIRECTORY)

    with open(OUTPUT_FILE, "w") as f:
        json.dump(results, f, indent=2)

    print("\n--- ALL SOLUTIONS SAVED ---\n")
    print(f"Saved to {OUTPUT_FILE}")