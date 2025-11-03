import { MathJax, MathJaxContext } from "better-react-mathjax";

const config = {
  tex: {
    inlineMath: [["\\(", "\\)"]],
    displayMath: [["\\[", "\\]"]],
  },
};

export default function LatexView({ latex }) {
  if (!latex) return null;
  return (
    <MathJaxContext version={3} config={config}>
      <div className="prose max-w-none">
        <MathJax dynamic>{latex}</MathJax>
      </div>
    </MathJaxContext>
  );
}