import { GenerateButton } from "../components/Buttons";
import React, { useEffect, useState } from "react";
import axios from "axios";
import LatexView from "../components/LatexView";
import SubjectTopicPicker from "../components/SubjectTopicPicker";
import { API_URL } from "../index.js";
import { MathJax, MathJaxContext } from "better-react-mathjax";

/* ---------------- LOADER ---------------- */
const Loader = ({ text = "Loading..." }) => (
  <div className="flex items-center gap-3 text-sm text-gray-600">
    <div className="w-4 h-4 border-2 border-gray-300 border-t-gray-700 rounded-full animate-spin"></div>
    <span>{text}</span>
  </div>
);

/* ---------------- COMPONENT ---------------- */
function Generate() {
  const [selectedTopics, setSelectedTopics] = useState([]);
  const [generatedLatex, setGeneratedLatex] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  const [activeTab, setActiveTab] = useState("solution");

  const [diagramLoading, setDiagramLoading] = useState(false);
  const [diagramError, setDiagramError] = useState("");
  const [diagramSVG, setDiagramSVG] = useState("");
  const [diagramTikz, setDiagramTikz] = useState("");

  const [solutionLoading, setSolutionLoading] = useState(false);
  const [solutionError, setSolutionError] = useState("");
  const [generatedSolution, setGeneratedSolution] = useState("");

  const [uploadedFile, setUploadedFile] = useState(null);
  const [feedbackLoading, setFeedbackLoading] = useState(false);
  const [feedbackError, setFeedbackError] = useState("");
  const [feedbackResult, setFeedbackResult] = useState(null);

  const [subject, setSubject] = useState("Mathematics Advanced");

  /* ---------------- HELPERS ---------------- */
  const handleFileUpload = (e) => {
    const file = e.target.files[0];
    if (!file) return;
    setUploadedFile(file);
  };

  const toBase64 = (file) =>
    new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.readAsDataURL(file);
      reader.onload = () => resolve(reader.result.split(",")[1]);
      reader.onerror = reject;
    });

  /* ---------------- API CALLS ---------------- */

  const handleGenerate = async () => {
    setLoading(true);
    setErrorMsg("");

    try {
      const res = await axios.post(`${API_URL}/generate-question-by-topics`, {
        topics: selectedTopics,
        exemplar_count: 5,
        temperature: 0.5,
        subject,
      });

      setGeneratedLatex(res.data?.latex ?? "");
      setGeneratedSolution("");
      setFeedbackResult("");
      setDiagramSVG("");
      setDiagramTikz("");
    } catch (err) {
      setErrorMsg(err?.response?.data?.error || "Failed to generate question.");
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateSolution = async () => {
    if (!generatedLatex) {
      setSolutionError("Generate a question first.");
      return;
    }

    setSolutionLoading(true);
    setSolutionError("");

    try {
      const res = await axios.post(`${API_URL}/generate-solution-text`, {
        question_text: generatedLatex,
        subject,
      });

      setGeneratedSolution(res.data.generated_solution);
    } catch {
      setSolutionError("Failed to generate solution.");
    } finally {
      setSolutionLoading(false);
    }
  };

  const handleGenerateDiagram = async () => {
    if (!generatedLatex) {
      setDiagramError("Generate a question first.");
      return;
    }

    setDiagramLoading(true);
    setDiagramError("");

    try {
      const res = await axios.post(`${API_URL}/generate-diagram-for-question`, {
        question_latex: generatedLatex,
        topics: selectedTopics,
        render_target: "svg",
      });

      const { svg, tikz_code } = res.data || {};
      if (svg) setDiagramSVG(svg);
      else if (tikz_code) setDiagramTikz(tikz_code);
      else setDiagramError("No diagram returned.");
    } catch {
      setDiagramError("Failed to generate diagram.");
    } finally {
      setDiagramLoading(false);
    }
  };

  const handleGenerateFeedback = async () => {
    if (!uploadedFile) {
      setFeedbackError("Upload a solution first.");
      return;
    }

    setFeedbackLoading(true);
    setFeedbackError("");

    try {
      const base64 = await toBase64(uploadedFile);

      const res = await axios.post(`${API_URL}/generate_feedback`, {
        image_base64: base64,
        question_text: generatedLatex,
        subject,
      });

      const feedback =
        typeof res.data.feedback === "string"
          ? JSON.parse(res.data.feedback)
          : res.data.feedback;

      setFeedbackResult(feedback);
    } catch {
      setFeedbackError("Failed to generate feedback.");
    } finally {
      setFeedbackLoading(false);
    }
  };

  useEffect(() => {
    if (!diagramTikz) return;
    setTimeout(() => {
      if (window.renderTikz) window.renderTikz();
    }, 0);
  }, [diagramTikz]);


  const cleanLatex = (str) => {
  if (!str) return "";

  return str
    // fix double escaped backslashes from JSON
    .replace(/\\\\/g, "\\")
    // remove accidental escaped parentheses (extra layer)
    .replace(/\\\(/g, "\\(")
    .replace(/\\\)/g, "\\)")
    // optional: trim weird spacing
    .replace(/\s+/g, " ")
    .trim();
};

  /* ---------------- UI ---------------- */

  return (
    <div className="p-6">
      {/* GLOBAL OVERLAY */}

      <div className="flex flex-col md:flex-row gap-8">

        {/* LEFT PANEL */}
        <div className="w-full md:w-[40%]">
          <h1 className="text-2xl font-bold mb-4">Generate Question</h1>

          <SubjectTopicPicker
            initialSubject={subject}
            onChange={(s, topics) => {
              setSubject(s);
              setSelectedTopics(topics);
            }}
          />

          <div className="mt-6 flex items-center gap-3">
            <GenerateButton
              onClick={handleGenerate}
              disabled={loading || selectedTopics.length === 0}
            />
            {loading && <Loader text="Generating question..." />}
          </div>

          {errorMsg && <p className="text-red-600 mt-2">{errorMsg}</p>}
        </div>

        {/* RIGHT PANEL */}
        <div className="w-full md:w-[60%] flex flex-col gap-4">

          {/* QUESTION */}
          <div className="rounded-2xl border p-4 min-h-[200px]">
            {loading ? (
              <div className="animate-pulse space-y-3">
                <div className="h-4 bg-gray-200 rounded w-3/4"></div>
                <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                <div className="h-4 bg-gray-200 rounded w-2/3"></div>
              </div>
            ) : generatedLatex ? (
              <LatexView latex={generatedLatex} />
            ) : (
              <p className="text-gray-500">Generated question appears here</p>
            )}
          </div>

          {/* TABS */}
          <div className="flex gap-2">
            {["solution", "feedback", "diagram"].map((tab) => (
              <button
                key={tab}
                onClick={() => setActiveTab(tab)}
                className={`px-4 py-2 rounded-xl capitalize ${
                  activeTab === tab
                    ? "text-white " +
                      (tab === "solution"
                        ? "bg-green-600"
                        : tab === "feedback"
                        ? "bg-purple-600"
                        : "bg-blue-600")
                    : "bg-gray-200"
                }`}
              >
                {tab}
              </button>
            ))}
          </div>

          {/* SOLUTION TAB */}
          {activeTab === "solution" && (
            <>
              <button
                onClick={handleGenerateSolution}
                disabled={solutionLoading}
                className="bg-green-600 text-white px-4 py-2 rounded-xl disabled:opacity-50"
              >
                {solutionLoading ? "Generating..." : "Generate Solution"}
              </button>


              {solutionError && (
                <p className="text-red-500 text-sm">{solutionError}</p>
              )}

              <div className="border p-4 rounded-2xl">
                {solutionLoading ? (
                  <Loader text="Generating solution..." />
                ) : generatedSolution ? (
                  <LatexView latex={cleanLatex(generatedSolution)} />
                ) : (
                  <p className="text-gray-500">Solution appears here</p>
                )}
              </div>
            </>
          )}

          {/* FEEDBACK TAB */}
          {activeTab === "feedback" && (
            <>
              <p className="text-sm text-gray-600">Upload an image of your solution to get AI-generated feedback on its correctness and areas for improvement.</p>
              <input type="file" onChange={handleFileUpload} />

              <button
                onClick={handleGenerateFeedback}
                disabled={feedbackLoading}
                className="bg-purple-600 text-white px-4 py-2 rounded-xl disabled:opacity-50"
              >
                {feedbackLoading ? "Analysing..." : "Generate Feedback"}
              </button>

              {feedbackError && (
                <p className="text-red-600">{feedbackError}</p>
              )}

             <div className="border p-4 rounded-2xl">
              {feedbackLoading ? (
                <Loader text="Marking solution..." />
              ) : feedbackResult ? (
              <div className="text-sm space-y-4">

                {/* SUMMARY */}

             <h3 className="font-semibold mb-3">Marking</h3>

            <p className="text-lg font-bold mb-3">
              {feedbackResult.marks_awarded} / {feedbackResult.total_marks}
            </p>


                {/* TABLE */}
              <div>
                  <strong>Marking:</strong>
                <MathJaxContext>
  <MathJax dynamic>
              <table className="w-full text-sm border border-gray-300">
                    <thead>
                      <tr className="bg-gray-100">
                        <th className="border px-2 py-1">Part</th>
                        <th className="border px-2 py-1">Criteria</th>
                        <th className="border px-2 py-1">Marks</th>
                        <th className="border px-2 py-1">Comment</th>
                      </tr>
                    </thead>
                          <tbody>
                      {feedbackResult.marking_table?.map((row, i) => (
                        <tr key={i}>
                          <td className="border px-2 py-1">({row.part})</td>

                          {/* ✅ Criteria with LaTeX */}
                          <td className="border px-2 py-1">
                             <LatexView latex={cleanLatex(row.criterion)} />
                           
                          </td>

                          {/* Marks */}
                          <td className="border px-2 py-1">
                            {row.marks_awarded} / {row.max_marks}
                          </td>

                          {/* ✅ Comment with LaTeX */}
                          <td className="border px-2 py-1">
                            <LatexView latex={cleanLatex(row.comment)} />
                            
                            {/* OPTIONAL: show correct working */}
                            {row.correct_working && (
                              <div className="mt-1 text-gray-600">
                                <LatexView latex={cleanLatex(row.correct_working)} />
                              </div>
                            )}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>


                   <div className="mt-3">
                      <strong>Summary:</strong>
                      <div className="text-sm">
                        <LatexView latex={feedbackResult.summary} />
                      </div>
                    </div>

                    <div className="mt-2">
                      <strong>Improvements:</strong>
                      <ul className="list-disc ml-5 text-sm">
                        {feedbackResult.improvements?.map((imp, i) => (
                          <li key={i}>
                            <LatexView latex={imp} />
                          </li>
                        ))}
                      </ul>
                    </div>
                  </MathJax>
                  </MathJaxContext>



                </div>

              </div>
              ) : (
                <p className="text-gray-500">Feedback appears here</p>
              )}
            </div>
            </>
          )}

          {/* DIAGRAM TAB */}
          {activeTab === "diagram" && (
            <>
              <button
                onClick={handleGenerateDiagram}
                disabled={diagramLoading}
                className="bg-blue-600 text-white px-4 py-2 rounded-xl disabled:opacity-50"
              >
                {diagramLoading ? "Generating..." : "Generate Diagram"}
              </button>

              {diagramError && (
                <p className="text-red-500 text-sm">{diagramError}</p>
              )}

              <div className="border p-4 rounded-2xl min-h-[180px] flex items-center justify-center">
                {diagramLoading ? (
                  <Loader text="Rendering diagram..." />
                ) : diagramSVG ? (
                  <div
                    dangerouslySetInnerHTML={{ __html: diagramSVG }}
                  />
                ) : diagramTikz ? (
                  <pre className="tikzjax">{diagramTikz}</pre>
                ) : (
                  <p className="text-gray-500">Diagram appears here</p>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default Generate;
