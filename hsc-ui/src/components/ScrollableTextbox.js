import React, { useState, useEffect } from "react";
import axios from "axios";
import { MathJaxContext } from "better-react-mathjax";
import { DeleteButton } from "../components/Buttons";
import LatexView from "../components/LatexView";
import { API_URL } from "../index.js";

/* ------------------ REVAMP POPUP ------------------ */
const RevampPopup = ({ questionLatex, subject, onClose }) => {
  const [solution, setSolution] = useState("");
  const [loadingSolution, setLoadingSolution] = useState(false);

  const [file, setFile] = useState(null);
  const [feedback, setFeedback] = useState(null);
  const [loadingFeedback, setLoadingFeedback] = useState(false);

  const toBase64 = (file) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result.split(",")[1]);
      reader.onerror = reject;
    });

  /* -------- SOLUTION -------- */
  const handleGenerateSolution = async () => {
    setLoadingSolution(true);
    try {
      const res = await axios.post(`${API_URL}/generate-solution`, {
        question_text: questionLatex,
        subject,
      });
      setSolution(res.data.generated_solution);
    } catch {
      alert("Failed to generate solution");
    } finally {
      setLoadingSolution(false);
    }
  };

  /* -------- FEEDBACK -------- */
  const handleGenerateFeedback = async () => {
    if (!file) return;

    setLoadingFeedback(true);

    try {
      const base64 = await toBase64(file);

      const res = await axios.post(`${API_URL}/generate_feedback`, {
        image_base64: base64,
        question_text: questionLatex,
        subject,
      });

      const parsed =
        typeof res.data.feedback === "string"
          ? JSON.parse(res.data.feedback)
          : res.data.feedback;

      setFeedback(parsed);
    } catch {
      alert("Failed to generate feedback");
    } finally {
      setLoadingFeedback(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-40 backdrop-blur-sm">
      <div className="bg-white rounded-2xl shadow-xl p-6 w-full max-w-3xl relative overflow-y-auto max-h-[90vh]">

        {/* CLOSE */}
        <button
          onClick={onClose}
          className="absolute top-3 right-3 text-gray-400 hover:text-red-500 text-xl"
        >
          ✕
        </button>

        <h2 className="text-xl font-semibold mb-4">
          Revamped Question
        </h2>

        {/* QUESTION */}
        <MathJaxContext>
          <LatexView latex={questionLatex} />
        </MathJaxContext>

        {/* SOLUTION */}
        <div className="mt-6">
          <button
            onClick={handleGenerateSolution}
            className="bg-green-600 text-white px-3 py-1 rounded"
          >
            {loadingSolution ? "Generating..." : "Generate Solution"}
          </button>

          {solution && (
            <div className="mt-3 p-3 border rounded bg-gray-50">
              <strong>Solution</strong>
              <LatexView latex={solution} />
            </div>
          )}
        </div>

        {/* FEEDBACK */}
        <div className="mt-6">
          <p className="font-semibold">Upload a solution to get feedback:</p>
          <input
            type="file"
            onChange={(e) => setFile(e.target.files[0])}
          />

          <button
            onClick={handleGenerateFeedback}
            className="bg-purple-600 text-white px-3 py-1 rounded ml-2"
          >
            {loadingFeedback ? "Generating..." : "Generate Feedback"}
          </button>

          {feedback && (
            <div className="mt-3 border p-3 rounded">

              <p className="font-bold">
                {feedback.marks_awarded} / {feedback.total_marks}
              </p>

              <table className="w-full text-sm border mt-2">
                <thead>
                  <tr>
                    <th>Part</th>
                    <th>Criteria</th>
                    <th>Marks</th>
                    <th>Comment</th>
                  </tr>
                </thead>
                <tbody>
                  {feedback.marking_table?.map((row, i) => (
                    <tr key={i}>
                      <td>{row.part}</td>
                      <td>{row.criterion}</td>
                      <td>{row.marks_awarded}/{row.max_marks}</td>
                      <td>{row.comment}</td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <p className="mt-2"><strong>Summary:</strong> {feedback.summary}</p>

              <ul className="list-disc ml-5">
                {feedback.improvements?.map((imp, i) => (
                  <li key={i}>{imp}</li>
                ))}
              </ul>

            </div>
          )}
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
      <div className="h-screen overflow-y-auto p-4 border rounded-lg bg-white shadow w-full text-gray-700">

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
                  onClick={() => onGenerateSolution(q, index)}
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
              <p className="font-semibold mt-4">Upload your solution for feedback:</p>
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
          subject={subject}
          onClose={() => setShowPopup(false)}
        />
      )}
    </MathJaxContext>
  );
};

export default ScrollableTextBox;