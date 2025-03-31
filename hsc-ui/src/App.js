import React, { useState } from "react";
import axios from "axios";
import "./App.css";

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

function App() {
  const [file, setFile] = useState(null);
  const [images, setImages] = useState([]);
  const [correctedTopics, setCorrectedTopics] = useState({});

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
    const payload = Object.entries(correctedTopics).map(([id, topics]) => ({
      id,
      corrected_topics: topics,
    }));

    try {
      await axios.post("http://localhost:8000/submit_correction/", payload);
      alert("Corrections submitted!");
    } catch (err) {
      alert("Failed to submit corrections.");
      console.error(err);
    }
  };

  console.log("Images:", images);

  return (
    <div className="App">
      <h1>📄 HSC Maths Image Classifier</h1>
      <input type="file" accept=".pdf" onChange={(e) => setFile(e.target.files[0])} />
      <button onClick={uploadFile} disabled={!file} style={{ marginBottom: 20 }}>
        Upload & Classify
      </button>

      {images.length > 0 && (
        <div>
          {images.map((img) => (
            <div key={img.id} style={{ marginBottom: 40 }}>
              <img
                src={`data:image/png;base64,${img.base64}`}
                alt={`question-${img.id}`}
                style={{ maxWidth: "100%", border: "1px solid #ccc" }}
              />
              <div style={{ marginTop: 10 }}>
                <p><strong>GPT Prediction:</strong> {img.topics?.join(", ") || "No prediction"}</p>
                <label>Correct topics:</label>
                <select
                  multiple
                  value={correctedTopics[img.id] || []}
                  onChange={(e) => handleTopicChange(img.id, e.target.selectedOptions)}
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

          <button onClick={submitCorrections} style={{ marginTop: 30 }}>
            Submit All Corrections
          </button>
        </div>
      )}
    </div>
  );
}

export default App;
