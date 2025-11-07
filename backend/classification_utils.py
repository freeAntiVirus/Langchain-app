
import re
import pdfplumber
from PIL import Image
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import pytesseract
import ast
import random
import os


# Find absolute path to the binary inside backend/bin
# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# pytesseract.pytesseract.tesseract_cmd = os.path.join(os.getcwd(), "bin", "pytesseract-0.3.13")


def generate_unique_question_id(existing_ids, max_tries=10):
    for _ in range(max_tries):
        qid = str(random.randint(100000, 999999))
        if qid not in existing_ids:
            return qid
    raise Exception("Failed to generate unique QuestionId after multiple attempts.")

# Extract text from PDF pages
def extract_text_from_pdf(file_path):
    images = []
    with pdfplumber.open(file_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            images.append({
                "id": f"page_{i+1}",
                "text": text,
                "topics": []
            })
    return images

def extract_lines_with_coordinates(pil_img):
    ocr_data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT)
    lines = []
    current_line = ""
    last_line_num = -1
    last_block_num = -1
    last_top = -1

    for i in range(len(ocr_data['text'])):
        word = ocr_data['text'][i]
        if not word.strip():
            continue

        line_num = ocr_data['line_num'][i]
        block_num = ocr_data['block_num'][i]
        top = ocr_data['top'][i]

        if line_num != last_line_num or block_num != last_block_num:
            if current_line:
                lines.append((last_top, current_line.strip()))
            current_line = word
            last_top = top
        else:
            current_line += " " + word

        last_line_num = line_num
        last_block_num = block_num

    if current_line:
        lines.append((last_top, current_line.strip()))

    return lines


def extract_question_coordinates_from_lines(lines, openai_api_key):
    chat = ChatOpenAI(model_name="gpt-4", temperature=0, openai_api_key=openai_api_key)
    prompt = (
        "You are given a list of lines with their Y-coordinates from the top of a page.\n"
        "Identify the lines that mark the start of **new questions**.\n\n"

        "### Instructions:\n"
        "- If a line starts with a question number (e.g. 'Question 12 (3 marks)') or just a number like '12', and it is followed by lines continuing the prompt, only mark the first line. Do NOT mark those continuation lines as new questions — they are part of the same question block.\n"
        "- A question only ends when a new question starts \n"
        "- If a line contains only a question number (like '4' or 'Question 4') and is immediately followed by another line of text, treat both as the same question. Only mark the number line as the start.\n"
        "- Do NOT mark answer options like 'A.', 'B.', 'C.', or 'D.' as new questions.\n"
        "- Do NOT treat sub-parts like (a), (b), (c) as separate questions — they are part of the main question.\n"
        "- Use your reasoning: a question ends only after its options (if present) are listed, or when a completely new topic/question begins.\n\n"

        "Return a valid Python list of integers representing the **Y-coordinates** where new questions begin.\n"
        "Do not include any explanation. Do not include any question text.\n"
        "Example output: [100, 400, 700]\n\n"

        f"lines = {lines}"
    )

    response = chat([HumanMessage(content=prompt)])
    print("GPT Response:", response.content)

    try:
        result = ast.literal_eval(response.content)
        if isinstance(result, list) and all(isinstance(y, int) for y in result):
            return result
        else:
            print("Parsed result not valid:", result)
            return []
    except Exception as e:
        print("Failed to parse GPT output as list of Y-coordinates:", e)
        return []
    

def crop_image_by_y_coords(img, y_start, y_end):
    return img.crop((0, y_start, img.width, y_end))

def extract_text_with_ocr(pil_image):
    return pytesseract.image_to_string(pil_image)

def _to_rgb(img):
    return img.convert("RGB") if img.mode != "RGB" else img

def _resize_to_height(img, target_h):
    w, h = img.size
    if h == target_h:
        return img
    new_w = int(w * (target_h / h))
    return img.resize((new_w, target_h), Image.LANCZOS)

def _stitch_double_spreads(pages, gap=32, bg_color="white"):
    """
    Arrange pages as 2 columns per row (double-page spreads), stacked into one image.
    Odd final page is centered in its row.
    """
    pages = [_to_rgb(p) for p in pages]

    # Build row images (each row has up to 2 pages)
    rows = []
    for i in range(0, len(pages), 2):
        left = pages[i]
        right = pages[i+1] if i+1 < len(pages) else None

        # Unify heights within the row
        target_h = max(left.height, right.height if right else 0)
        left_r = _resize_to_height(left, target_h)
        if right:
            right_r = _resize_to_height(right, target_h)

        if right:
            row_w = left_r.width + gap + right_r.width
            row = Image.new("RGB", (row_w, target_h), bg_color)
            x = 0
            row.paste(left_r, (x, 0)); x += left_r.width + gap
            row.paste(right_r, (x, 0))
        else:
            # Single page centered
            row_w = left_r.width + 2 * gap
            row = Image.new("RGB", (row_w, target_h), bg_color)
            x = (row_w - left_r.width) // 2
            row.paste(left_r, (x, 0))

        rows.append(row)

    # Stack rows vertically with gaps
    if not rows:
        raise ValueError("No pages to stitch.")
    vgap = gap
    total_w = max(r.width for r in rows)
    total_h = sum(r.height for r in rows) + vgap * (len(rows) - 1)

    canvas = Image.new("RGB", (total_w, total_h), bg_color)
    y = 0
    for r in rows:
        # center each row horizontally on the canvas
        x = (total_w - r.width) // 2
        canvas.paste(r, (x, y))
        y += r.height + vgap

    return canvas

from collections import Counter

def tally_topics(corrections_context: str):
    """
    Extracts all topic names from the corrections context string and counts frequency.
    Returns a Counter object sorted by most common.
    """
    topics_list = []

    # Regex to find anything inside "['...']" or list-like parts
    matches = re.findall(r"\['([^]]+)'\]", corrections_context)
    for match in matches:
        # match could be "MA-F1: ..., 'MA-C3: ...'"
        for topic in [t.strip().strip("'").strip('"') for t in match.split(",")]:
            if topic:
                topics_list.append(topic)

    return Counter(topics_list)


# NOTE: This function contains the cropping logic which we've decided to remove for now
# def extract_images_from_pdf(file_path, openai_api_key):
#     images = []
#     with pdfplumber.open(file_path) as pdf:
#         for i, page in enumerate(pdf.pages):
#             img = page.to_image(resolution=200).original

#             lines = extract_lines_with_coordinates(img)

#             print("Raw lines:", lines)
#             y_coords = extract_question_coordinates_from_lines(lines, openai_api_key)
#             print("Raw Y-coordinates:", y_coords)

#             cropped_questions = []
#             existing_ids = {doc.metadata.get("question_id") for doc in vectorstore.docstore._dict.values()}
#             for idx, y_start in enumerate(y_coords):
#                 if idx + 1 < len(y_coords):
#                     y_end = y_coords[idx + 1]
#                 else:
#                     y_end = img.height

#                 leeway = 20
#                 y_start_leeway = max(y_start - leeway, 0)
#                 y_end_leeway = min(y_end, img.height)

#                 cropped_img = crop_image_by_y_coords(img, y_start_leeway, y_end_leeway)
#                 text = extract_text_with_ocr(cropped_img)
#                 buffered = io.BytesIO()
#                 cropped_img.save(buffered, format="PNG")
#                 img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

#                 qid = generate_unique_question_id(existing_ids)
#                 existing_ids.add(qid)
#                 cropped_questions.append({
#                     "id": qid,
#                     "base64": img_str,
#                     "text": text,
#                     "topics": []
#                 })

#             images.extend(cropped_questions)
#     return images