import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import { MathJaxContext } from "better-react-mathjax";
import { DeleteButton } from "../components/Buttons";
import LatexView from "../components/LatexView";
import { API_URL } from "../index.js";

/* ------------------ REVAMP POPUP ------------------ */
const RevampPopup = ({ questionLatex, onClose }) => {
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

        <h2 className="text-xl font-semibold mb-4 text-gray-800">
          🔁 Revamped Question
        </h2>

        <MathJaxContext>
          <div ref={captureRef}>
            <div className="overflow-auto px-1 max-h-[70vh]">
              <LatexView latex={questionLatex} />
            </div>
          </div>
        </MathJaxContext>

        <div className="mt-6 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  );
};

/* ------------------ MAIN COMPONENT ------------------ */
const ScrollableTextBox = ({
  questions = [],
  onQuestionsUpdate,
  subject,

  // FROM PARENT
  onGenerateSolution,
  solutions,
  loadingSolutions,

  onFileUpload,
  onGenerateFeedback,
  feedbackResults,
  feedbackLoading
}) => {
  const [revampQuestion, setRevampQuestion] = useState("");
  const [showPopup, setShowPopup] = useState(false);
  const [loadingIndex, setLoadingIndex] = useState(null);
  const [localQuestions, setLocalQuestions] = useState(questions);

  useEffect(() => {
    setLocalQuestions(questions);
    if (onQuestionsUpdate) {
      onQuestionsUpdate(questions);
    }
  }, [questions, onQuestionsUpdate]);

  /* -------- REVAMP -------- */
  const fetchRevamp = async (question, index) => {
    try {
      setLoadingIndex(index);

      const res = await axios.post(`${API_URL}/revamp_question/`, {
        img: {
          id: question.id || question.QuestionId,
          base64: question.base64,
          text: question.text,
          topics: question.topics,
        },
        subject: subject,
      });

      setRevampQuestion(res.data.revamped_question_latex);
      setShowPopup(true);
    } catch (err) {
      console.error(err);
      alert("Failed to generate similar question.");
    } finally {
      setLoadingIndex(null);
    }
  };

  /* -------- DELETE -------- */
  const handleDelete = (indexToDelete) => {
    const updated = localQuestions.filter((_, i) => i !== indexToDelete);
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
              {/* IMAGE */}
              {q.base64 && (
                <img
                  src={`data:image/png;base64,${q.base64}`}
                  alt={`question-${index}`}
                  className="w-full border mb-4"
                />
              )}

              {/* TOPICS */}
              <div className="text-sm mb-2">
                <strong>Topics:</strong>{" "}
                {q.topics?.join(", ") || "None"}
              </div>

              {/* BUTTONS */}
              <div className="absolute top-2 right-2 flex gap-2 flex-wrap">

                {/* SOLUTION */}
                <button
                  onClick={() => onGenerateSolution(q.text || q, index)}
                  className="bg-green-500 px-2 py-1 rounded text-sm text-white"
                >
                  {loadingSolutions?.[index] ? "Loading..." : "Solution"}
                </button>

                {/* REVAMP */}
                <button
                  onClick={() => fetchRevamp(q, index)}
                  className="bg-yellow-300 px-2 py-1 rounded text-sm"
                >
                  {loadingIndex === index ? "Loading..." : "Revamp"}
                </button>

                <DeleteButton onClick={() => handleDelete(index)} />
              </div>

              {/* SOLUTION OUTPUT */}
              {solutions?.[index] && (
                <div className="mt-4 p-3 bg-gray-50 border rounded">
                  <h4 className="font-semibold mb-2">Solution</h4>
                  <LatexView latex={solutions[index]} />
                </div>
              )}

              {/* FILE UPLOAD */}
              <div className="mt-3">
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => onFileUpload(e, index)}
                  className="text-sm"
                />
              </div>

              {/* GENERATE FEEDBACK */}
              <button
                onClick={() => onGenerateFeedback(q.text || q, index)}
                className="mt-2 px-3 py-1 bg-purple-600 text-white rounded"
              >
                {feedbackLoading?.[index] ? "Generating..." : "Generate Feedback"}
              </button>

              {/* FEEDBACK OUTPUT */}
              {feedbackResults?.[index] && (
                <div className="mt-3 border p-3 rounded bg-white">

                  <p className="font-bold">
                    {feedbackResults[index].marks_awarded} /{" "}
                    {feedbackResults[index].total_marks}
                  </p>

                 <table className="w-full text-sm border border-gray-300 mt-2 table-fixed">
  <thead>
    <tr className="bg-gray-100 text-left">
      <th className="border px-2 py-1 w-[8%]">Part</th>
      <th className="border px-2 py-1 w-[32%]">Criteria</th>
      <th className="border px-2 py-1 w-[15%]">Marks</th>
      <th className="border px-2 py-1 w-[45%]">Comment</th>
    </tr>
  </thead>

  <tbody>
    {feedbackResults[index].marking_table?.map((row, i) => (
      <tr key={i} className="align-top">

        {/* PART */}
        <td className="border px-2 py-1 font-semibold">
          ({row.part})
        </td>

        {/* CRITERIA */}
        <td className="border px-2 py-1 whitespace-pre-wrap">
          {row.criterion}
        </td>

        {/* MARKS */}
        <td className="border px-2 py-1 text-center font-medium">
          {row.marks_awarded} / {row.max_marks}
        </td>

        {/* COMMENT */}
        <td className="border px-2 py-1 whitespace-pre-wrap">
          {row.comment}
        </td>

      </tr>
    ))}
  </tbody>
</table>

                  <div className="mt-2">
                    <strong>Summary:</strong>
                    <LatexView latex={feedbackResults[index].summary} />
                  </div>

                  <div className="mt-2">
                    <strong>Improvements:</strong>
                    <ul className="list-disc ml-5 text-sm">
                      {feedbackResults[index].improvements?.map((imp, i) => (
                        <li key={i}>
                          <LatexView latex={imp} />
                        </li>
                      ))}
                    </ul>
                  </div>

                </div>
              )}
            </div>
          ))
        )}
      </div>

      {/* POPUP */}
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