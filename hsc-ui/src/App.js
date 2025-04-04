import React, { useState } from "react";
import axios from "axios";
import "./App.css";
import { MathJaxContext, MathJax } from "better-react-mathjax";

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
          <MathJax dynamic>{questionLatex}</MathJax>
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

  const handleTopicChange = (imageId, selectedOptions) => {
    const selectedValues = Array.from(selectedOptions, (opt) => opt.value);
    setCorrectedTopics((prev) => ({ ...prev, [imageId]: selectedValues }));
  };

  const submitCorrections = async () => {
    const payload = Object.entries(correctedTopics).map(([id, topics]) => {
      const base64 = images.find((img) => img.id === id)?.base64 || "";
      return {
        id,
        corrected_topics: topics,
        base64: base64,
      };
    });

    try {
      await axios.post("http://localhost:8000/submit_corrections/", payload);
      alert("Corrections submitted!");
    } catch (err) {
      alert("Failed to submit corrections.");
      console.error(err);
    }
  };

  const fetchRevamp = async (img) => {
    try {
      const res = await axios.post("http://localhost:8000/revamp_question/", { img });
      console.log("🔄 Response from /revamp_question/:", res.data);
      setRevampQuestion(res.data.revamped_question_latex);
      setShowPopup(true);
    } catch (err) {
      alert("Failed to generate similar question.");
      console.error(err);
    }
  };
  

  return (
    <MathJaxContext>
      <div className="App p-6">
        <h1 className="text-2xl font-bold mb-4">📄 HSC Maths Image Classifier</h1>
  
        <input type="file" accept=".pdf" onChange={(e) => setFile(e.target.files[0])} />
  
        <button
          onClick={uploadFile}
          disabled={!file}
          className="mt-2 mb-6 bg-blue-600 text-white px-4 py-2 rounded disabled:opacity-50"
        >
          Upload & Classify
        </button>
  
        {images.length > 0 && (
          <div className="space-y-8">
            {images.map((img) => (
              <div key={img.id} className="relative border p-4 rounded shadow">
                <button
                  onClick={() => fetchRevamp(img)}
                  className="absolute top-2 right-2 bg-yellow-300 px-2 py-1 rounded hover:bg-yellow-400"
                >
                  Revamp 🔁
                </button>
                <img
                  src={`data:image/png;base64,${img.base64}`}
                  alt={`question-${img.id}`}
                  className="w-full border mb-4"
                />
                <div className="mt-2">
                  <p>
                    <strong>GPT Prediction:</strong>{" "}
                    {img.topics?.join(", ") || "No prediction"}
                  </p>
                  <label className="block mt-2">Correct topics:</label>
                  <select
                    multiple
                    value={correctedTopics[img.id] || []}
                    onChange={(e) => handleTopicChange(img.id, e.target.selectedOptions)}
                    className="w-full border rounded mt-1 p-1"
                  >
                    {topicList.map((topic) => (
                      <option key={topic} value={topic}>
                        {topic}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            ))}
  
            <button
              onClick={submitCorrections}
              className="bg-green-600 text-white px-4 py-2 rounded mt-6"
            >
              Submit All Corrections
            </button>
          </div>
        )}
  
        {showPopup && (
          <RevampPopup
            questionLatex={revampQuestion}
            onClose={() => setShowPopup(false)}
          />
        )}
      </div>
    </MathJaxContext>
  );
  
}

export default App;
