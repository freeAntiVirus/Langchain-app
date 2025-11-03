
import { GenerateButton } from "../components/Buttons";
import React, { useEffect, useState } from "react";
import axios from "axios";
import LatexView from "../components/LatexView";
import SubjectTopicPicker from "../components/SubjectTopicPicker"; // ⬅️ new
import {API_URL} from "../index.js"


function Generate() {
  const [selectedTopics, setSelectedTopics] = useState([]);
  const [generatedLatex, setGeneratedLatex] = useState("");
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState("");

  // Diagram state
  const [diagramLoading, setDiagramLoading] = useState(false);
  const [diagramError, setDiagramError] = useState("");
  const [diagramSVG, setDiagramSVG] = useState("");   // preferred (no browser libs)
  const [diagramTikz, setDiagramTikz] = useState(""); // fallback (render via tikzjax)
  const [subject, setSubject] = useState("Mathematics Advanced");

  const handleGenerate = async () => {
    setLoading(true);
    setErrorMsg("");
    setGeneratedLatex("");
    // clear any previous diagram
    setDiagramSVG("");
    setDiagramTikz("");
    setDiagramError("");

    try {
      const res = await axios.post(`${API_URL}/generate-question-by-topics`, {
        topics: selectedTopics,
        exemplar_count: 5,
        temperature: 0.5,
        subject: subject,
      });
      setGeneratedLatex(res.data?.latex ?? "");
    } catch (err) {
      console.error("Generate failed:", err);
      const msg =
        err?.response?.data?.error ||
        "Failed to generate question. Check server logs and topic selections.";
      setErrorMsg(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateDiagram = async () => {
    setDiagramLoading(true);
    setDiagramError("");
    setDiagramSVG("");
    setDiagramTikz("");

    if (!generatedLatex) {
      setDiagramLoading(false);
      setDiagramError("Generate a question first.");
      return;
    }

    try {
      const res = await axios.post(`${API_URL}/generate-diagram-for-question`, {
        question_latex: generatedLatex,
        topics: selectedTopics,
        render_target: "svg",      // ask backend for SVG (best UX)
        temperature: 0.2,
        hint: "Use clean exam style; include axes/labels if relevant."
      });

      const { svg, tikz_code, warnings } = res.data || {};
      if (svg) {
        setDiagramSVG(svg);
      } else if (tikz_code) {
        setDiagramTikz(tikz_code);
      } else {
        setDiagramError("No diagram returned.");
      }
      if (warnings?.length) {
        console.warn("Diagram warnings:", warnings);
      }
    } catch (err) {
      console.error("Diagram generation failed:", err);
      const msg =
        err?.response?.data?.error ||
        "Failed to generate diagram. Ensure backend has tectonic + dvisvgm for SVG, or fallback to TikZ.";
      setDiagramError(msg);
    } finally {
      setDiagramLoading(false);
    }
  };

  // Re-render TikZ client-side whenever we get TikZ (fallback path)
  useEffect(() => {
    if (!diagramTikz) return;
    const id = setTimeout(() => {
      if (window.renderTikz) window.renderTikz();
    }, 0);
    return () => clearTimeout(id);
  }, [diagramTikz]);

  return (
    <div className="p-6">
      <div className="flex flex-col md:flex-row gap-8">
        {/* Left Panel */}
        <div className="w-full md:w-[50%]">
          <h1 className="text-2xl font-bold mb-4">Generate Question</h1>
          <p className="mb-6">Pick your subject and topics, then generate a new HSC-style question.</p>

          <div className="flex flex-wrap gap-4 items-end">
            <div>
              <h2 className="text-sm font-medium mb-1">Select Subject</h2>
                <SubjectTopicPicker
                  initialSubject={subject}
                  onChange={(s, topics) => {
                    setSubject(s);
                    setSelectedTopics(topics);
                  }}
                />
            </div>
          
          </div>

          <div className="mt-12 flex items-center gap-3">
            <GenerateButton onClick={handleGenerate} disabled={loading || selectedTopics.length === 0} />
            {loading && <p className="text-sm text-gray-600">Generating…</p>}
          </div>
          {errorMsg && <p className="text-sm text-red-600 mt-2">{errorMsg}</p>}
        </div>

        {/* Right Panel */}
        <div className="w-full md:w-[50%] h-full flex flex-col gap-4">
          {/* Question */}
          <div className="rounded-2xl border p-4 min-h-[220px]">
            {generatedLatex ? (
              <LatexView latex={generatedLatex} />
            ) : (
              <p className="text-sm text-gray-500">Your generated question will appear here.</p>
            )}
          </div>

          {/* Generate Diagram Button */}
          <div className="flex items-center gap-3">
           <button
              onClick={handleGenerateDiagram}
              disabled={!generatedLatex || diagramLoading}
              className="px-4 py-2 rounded-xl bg-blue-600 text-white disabled:opacity-50"
              title={!generatedLatex ? "Generate a question first" : "Generate a diagram for this question"}
            >
              {diagramLoading ? "Generating Diagram…" : "Generate Diagram"}
            </button>
            {diagramError && <p className="text-sm text-red-600">{diagramError}</p>}
          </div>

          {/* Diagram Output */}
          <div className="rounded-2xl border p-4 min-h-[180px] flex items-center justify-center">
            {!diagramLoading && !diagramSVG && !diagramTikz && (
              <p className="text-sm text-gray-500">Your diagram will appear here.</p>
            )}

            {/* Prefer SVG (no browser libs needed) */}
            {diagramSVG && (
              <div
                className="max-w-full overflow-auto flex justify-center"
                dangerouslySetInnerHTML={{ __html: diagramSVG }}
              />
            )}

            {/* Fallback: TikZ via tikzjax */}
            {diagramTikz && !diagramSVG && (
              <pre className="tikzjax text-sm overflow-auto text-center">{diagramTikz}</pre>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default Generate;