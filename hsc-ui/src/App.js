import React, { useState } from "react";
import axios from "axios";
import "./App.css";
import { MathJaxContext, MathJax } from "better-react-mathjax";
import NavBar from "./components/NavBar"; // Adjust path if NavBar is in a different folder
import Home from "./pages/Home"; // These pages must exist
import ClassifyResources from "./pages/ClassifyResources"; // Adjust path if needed
import CreatePracticeSet from "./pages/CreatePracticeSet"; // Adjust path if needed
import Generate from "./pages/Generate"; // Adjust path if neede
import { Routes, Route } from "react-router-dom";
import { BrowserRouter as Router } from 'react-router-dom';

const topicList = [
  "MA-C1: Introduction to Differentiation",
  "MA-C2: Differential Calculus",
  "MA-C3: Applications of Differentiation",
  "MA-C4: Integral Calculus",
  "MA-E1: Logarithms and Exponentials",
  "MA-F1: Working with functions",
  "MA-F2: Graphing Techniques",
  "MA-S1: Probability and Discrete Probability Distributions",
  "MA-S2: Descriptive Statistics and Bivariate Data Analysis",
  "MA-S3: Random Variables",
  "MA-T1: Trigonometry and Measure of Angles",
  "MA-T2: Trigonometric Functions and Identities",
  "MA-T3: Trigonometric Functions and Graphs",
  "MA-M1: Modelling Financial Situations",
];

function convertToAlignedLatex(raw) {
  const lines = raw
    .split(/\\+/)
    .map(line => line.trim())
    .filter(Boolean)
    .map(line => `&\\text{${line}} \\\\`);
  
  return `\\[\n\\begin{aligned}\n${lines.join('\n')}\n\\end{aligned}\n\\]`;
}


const RevampPopup = ({ questionLatex, onClose }) => {
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40 backdrop-blur-sm">
      <div className="bg-white dark:bg-gray-800 rounded-2xl shadow-xl p-6 w-full max-w-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-3 right-3 text-gray-400 hover:text-red-500 text-xl"
        >
          ✕
        </button>
        <h2 className="text-xl font-semibold mb-4 text-gray-800 dark:text-white">🔁 Revamped Question</h2>
        <div className="text-gray-700 dark:text-gray-300 overflow-y-auto max-h-[60vh] px-1">
          <MathJax dynamic>{convertToAlignedLatex(questionLatex)}</MathJax>

        </div>
        <div className="mt-6 flex justify-end gap-2">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

function App() {
  const [file, setFile] = useState(null);
  const [images, setImages] = useState([]);
  const [correctedTopics, setCorrectedTopics] = useState({});
  const [revampQuestion, setRevampQuestion] = useState("");
  const [showPopup, setShowPopup] = useState(false);

  const uploadFile = async () => {
    if (!file) return;

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await axios.post("http://localhost:8000/classify/", formData);
      console.log("📦 Response from /classify_images/:", res.data);
      setImages(res.data.result);
    } catch (err) {
      alert("Failed to classify.");
      console.error(err);
    }
  };

  return (
    <Router>
      <NavBar />
      <div className="p-6">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/classifyResources" element={<ClassifyResources />} />
          <Route path="/practice" element={<CreatePracticeSet />} />
          <Route path="/generate" element={<Generate />} />
          {/* Add more routes as needed */}
        </Routes>
      </div>
    </Router>
  );
  
}

export default App;
