
# 🧠 HSC Maths Classifier (LangChain + GPT-4o + Vision)

This project allows you to upload a PDF of an HSC Mathematics exam paper, extract each question as an **image**, and automatically classify it into the correct topic(s) using GPT-4o Vision. Users can also correct the classifications and feed them back into the system to improve future predictions.

---

## 🚀 Setup Instructions

### 1. Clone the Repo
```bash
git clone https://github.com/freeAntiVirus/Langchain-app.git
cd langchain-app
```

---

### 2. Set Up the Backend (FastAPI + LangChain)

#### a. Navigate to backend folder
```bash
cd backend
```

#### b. Install dependencies
```bash
pip3 install -r requirements.txt
```

#### c. Create a `.env` file
Create a `.env` file in the `backend/` directory:

```bash
touch .env
```

Paste your OpenAI API key inside it:

```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

#### d. Start the backend server
```bash
python3 -m uvicorn main:app --reload
```

---

### 3. Set Up the Frontend (React)

#### a. Navigate to frontend folder
```bash
cd ../hsc-ui
```

#### b. Install dependencies
```bash
npm install
```

#### c. Start the development server
```bash
npm start
```

This will launch the app at [http://localhost:3000](http://localhost:3000).

---

## 🧾 Features

- Upload any PDF exam paper
- Extracts and displays each question as an **image**
- GPT-4o Vision classifies each question into HSC Maths topics
- Users can override predictions with dropdowns
- Feedback is stored and used to improve future classification

---

## 📂 Folder Structure

```
langchain-app/
│
├── backend/               # FastAPI backend
│   ├── main.py            # Main FastAPI app
│   ├── topics.txt         # Official topic list
│   ├── .env               # API key for OpenAI
│   └── requirements.txt   # Python dependencies
│
└── hsc-ui/                # React frontend
    └── App.js             # UI logic
```

---

## 📌 Dependencies

- FastAPI
- Uvicorn
- pdfplumber
- OpenAI (>= v1.0)
- LangChain
- FAISS
- Pillow (for image processing)
- React (frontend)

---

## 🧪 Example Use

Upload a scanned or digital PDF of an HSC paper, review the AI-classified topics, correct any mistakes, and help the model learn better over time.


## 📬 Contact

For help or ideas, feel free to reach out at [z5421904@ad.unsw.edu.au] or open an issue.

---

### Diagram Generation 

To generate diagram, paste tikz code into diagram.tex and run the following: 

`pdflatex diagram.tex`