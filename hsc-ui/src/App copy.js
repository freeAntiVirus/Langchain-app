import React, { useState } from "react";
import axios from "axios";
import "./App.css";

function App() {
  const [file, setFile] = useState(null);
  const [rawResult, setRawResult] = useState([]);
  const [corrected, setCorrected] = useState({});
  const [loading, setLoading] = useState(false);

  const allTopics = [
    "MA-C1: Introduction to Differentiation",
    "MA-C2: Differential Calculus",
    "MA-C3: Applications of Differentiation",
    "MA-C4: Integral Calculus",
    "MA-E1: Logarithms and Exponentials",
    "MA-F1: Working with Functions",
    "MA-F2: Graphing Techniques",
    "MA-S1: Probability and Discrete Probability Distributions",
    "MA-S2: Descriptive Statistics and Bivariate Data Analysis",
    "MA-S3: Random Variables",
    "MA-T1: Trigonometry and Measure of Angles",
    "MA-T2: Trigonometric Functions and Identities",
    "MA-T3: Trigonometric Functions and Graphs",
    "MA-M1: Modelling Financial Situations"
  ];

  const uploadFile = async () => {
    if (!file) return;
    setLoading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await axios.post("http://localhost:8000/classify/", formData);
      // console.log("RESSSS",res);
      // const parsed = JSON.parse(res.data.result); // Assuming backend returns JSON string
      // console.log("Parsed Result:", parsed);
      setRawResult(res.data.result);
      setCorrected({});
    } catch (err) {
      console.error(err);
      setRawResult([]);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (question, topics) => {
    setCorrected(prev => ({
      ...prev,
      [question]: topics
    }));
  };

  const submitCorrections = async () => {
    const corrections = Object.entries(corrected).map(([question, corrected_topics]) => ({
      question,
      corrected_topics,
    }));

    try {
      await axios.post("http://localhost:8000/submit_corrections/", corrections);
      alert("✅ Corrections submitted and stored!");
    } catch (err) {
      console.error(err);
      alert("Error submitting corrections.");
    }
  };

  console.log("Raw Result:", rawResult);
  return (
    <div className="App">
      <h1>📄 HSC Maths Classifier</h1>
      <input
        type="file"
        accept=".pdf"
        value={""} // force clear
        onChange={(e) => setFile(e.target.files[0])}
      />
      <button onClick={uploadFile} disabled={!file || loading}>
        {loading ? "Processing..." : "Classify"}
      </button>

      {rawResult.length > 0 && (
        <div style={{ textAlign: "left", marginTop: "30px", maxWidth: "600px", margin: "auto" }}>
          <h2>🔍 Review and Correct</h2>
          {rawResult.map((item, idx) => (
            <div key={idx} style={{ marginBottom: "15px" }}>
              <strong>{item.question}</strong>
              <br />
              <select
                multiple
                value={corrected[item.question] || item.topics}
                onChange={(e) =>
                  handleChange(
                    item.question,
                    Array.from(e.target.selectedOptions, (opt) => opt.value)
                  )
                }
                style={{ width: "100%", height: "100px", marginTop: "5px" }}
              >
                {allTopics.map((topic) => (
                  <option key={topic} value={topic}>
                    {topic}
                  </option>
                ))}
              </select>
            </div>
          ))}
          <button onClick={submitCorrections} style={{ marginTop: "20px", padding: "10px 20px" }}>
            ✅ Submit Corrections
          </button>
        </div>
      )}
    </div>
  );
}

export default App;
