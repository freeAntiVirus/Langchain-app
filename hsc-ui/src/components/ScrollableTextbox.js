import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import { MathJax, MathJaxContext } from "better-react-mathjax";
import { DeleteButton } from "../components/Buttons";
import html2canvas from "html2canvas";

const RevampPopup = ({ questionLatex, onClose}) => {
  const captureRef = useRef();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-2xl relative">
        <button
          onClick={onClose}
          className="absolute top-3 right-3 text-gray-400 hover:text-red-500 text-xl"
        >
          ✕
        </button>

        {/* Heading (not captured) */}
        <h2 className="text-xl font-semibold mb-4 text-gray-800">🔁 Revamped Question</h2>

        {/* This is the actual content that will be captured */}
        <div ref={captureRef}>
          <div className="overflow-auto px-1 max-h-[70vh]">
          <div ref={captureRef} className="inline-block w-full">
            <MathJax dynamic>{questionLatex}</MathJax>
          </div>
        </div>
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


const ScrollableTextBox = ({ questions = [], onQuestionsUpdate }) => {
  const [revampQuestion, setRevampQuestion] = useState("");
  const [showPopup, setShowPopup] = useState(false);
  const [loadingIndex, setLoadingIndex] = useState(null);
  const [localQuestions, setLocalQuestions] = useState(questions);

  useEffect(() => {
    setLocalQuestions(questions);
    if (onQuestionsUpdate) {
      onQuestionsUpdate(questions);
    }
  }, [questions]);

  const fetchRevamp = async (question, index) => {
    try {
      setLoadingIndex(index);
      const res = await axios.post("http://localhost:8000/revamp_question/", {
        img: {
          id: question.id || question.QuestionId,
          base64: question.base64,
          text: question.text,
          topics: question.topics,
        },
      });
      setRevampQuestion(res.data.revamped_question_latex);
      setShowPopup(true);
    } catch (err) {
      alert("Failed to generate similar question.");
      console.error(err);
    } finally {
      setLoadingIndex(null);
    }
  };

  const handleDelete = (indexToDelete) => {
    const updated = localQuestions.filter((_, index) => index !== indexToDelete);
    setLocalQuestions(updated);
    if (onQuestionsUpdate) {
      onQuestionsUpdate(updated);
    }
  };

  return (
    <MathJaxContext>
      <div className="h-[500px] overflow-y-auto p-4 border rounded-lg bg-white shadow w-full text-gray-700">
        {localQuestions.length === 0 ? (
          <p className="text-sm text-gray-500">No questions to display.</p>
        ) : (
          localQuestions.map((q, index) => (
            <div
              key={q.QuestionId || index}
              className="bg-white border rounded-lg shadow p-4 mb-6 relative"
            >
              {q.base64 && (
                <img
                  src={`data:image/png;base64,${q.base64}`}
                  alt={`question-${index + 1}`}
                  className="w-full border mb-4"
                />
              )}
              <div className="text-sm text-gray-800 mb-2">
                <strong>Topic Classification:</strong>{" "}
                {q.topics?.join(", ") || "No prediction"}
              </div>

              <div className="absolute top-2 right-2 flex gap-2">
                <button
                  onClick={() => fetchRevamp(q, index)}
                  className="bg-yellow-300 px-2 py-1 rounded text-sm hover:bg-yellow-400"
                  disabled={loadingIndex === index}
                >
                  {loadingIndex === index ? "Loading..." : "Revamp"}
                </button>
                <DeleteButton onClick={() => handleDelete(index)} />
              </div>
            </div>
          ))
        )}
      </div>

      {showPopup && (
        <RevampPopup
          questionLatex={revampQuestion}
          onClose={() => setShowPopup(false)}
        />
      )}
    </MathJaxContext>
  );
};

export default ScrollableTextBox;