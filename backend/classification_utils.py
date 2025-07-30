import asyncio
import json
import os
import io
import base64
import re
import pdfplumber
from PIL import Image
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from pydantic import BaseModel
from typing import List
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from openai import OpenAI
from langchain.schema import Document, HumanMessage
import pytesseract
from pydantic import BaseModel
from fastapi.responses import JSONResponse
import ast
from typing import List, Optional
from pymongo import MongoClient
import random
from pdf2image import convert_from_path

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