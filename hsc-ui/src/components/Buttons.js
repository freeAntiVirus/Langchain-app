import React from "react";
import jsPDF from "jspdf";

const GenerateButton = ({ onClick }) => {
  return (
    <button
      type="button"
      onClick={onClick}
      className="text-white bg-gradient-to-r from-cyan-500 to-blue-500 hover:bg-gradient-to-bl focus:ring-4 focus:outline-none focus:ring-cyan-300 dark:focus:ring-cyan-800 font-medium rounded-lg text-sm px-5 py-2.5 text-center"
    >
      Generate
    </button>
  );
};


const DeleteButton = ({ onClick, disabled = false }) => {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      className="bg-red-300 px-2 py-1 rounded text-sm hover:bg-red-400"
    >
      Delete
    </button>
  );
};

// Helper: Get image scaled dimensions
const getScaledImageDimensions = (base64, targetWidth = 180) => {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.src = `data:image/png;base64,${base64}`;

    img.onload = () => {
      const aspectRatio = img.height / img.width;
      const scaledHeight = targetWidth * aspectRatio;
      resolve({ width: targetWidth, height: scaledHeight });
    };

    img.onerror = (err) => {
      reject(err);
    };
  });
};

const DownloadPdfButton = ({ questions = [] }) => {
  const generatePdf = async () => {
    const doc = new jsPDF();
    let y = 20;
    const maxY = 280;

    // Title & Subtitle
    const title = "Custom Mathematics Practice Set";
    const subtitle = "Generated based on selected topics and question count.";

    doc.setFontSize(16);
    doc.setFont(undefined, "bold");
    const titleWidth = doc.getTextWidth(title);
    doc.text(title, (210 - titleWidth) / 2, y);
    y += 10;

    doc.setFontSize(12);
    doc.setFont(undefined, "normal");
    const subtitleWidth = doc.getTextWidth(subtitle);
    doc.text(subtitle, (210 - subtitleWidth) / 2, y);
    y += 15;

    // Helper to draw an image
    const drawImage = async (base64) => {
      const { width, height } = await getScaledImageDimensions(base64);
      if (y + height > maxY) {
        doc.addPage();
        y = 10;
      }
      doc.addImage(`data:image/png;base64,${base64}`, "PNG", 10, y, width, height);
      y += height + 10;
    };

    // Loop over original questions
    for (const q of questions) {
      if (q.base64) {
        await drawImage(q.base64);
      }

      const label = "Topic Classification:";
      const topicContent = q.topics?.join(", ") || "No prediction";

      // Bold label (centered)
      doc.setFont(undefined, "bold");
      const labelWidth = doc.getTextWidth(label);
      const labelX = (210 - labelWidth) / 2;
      doc.text(label, labelX, y);
      y += 6;

      // Normal content (wrapped, left-aligned under label)
      doc.setFont(undefined, "normal");
      const contentLines = doc.splitTextToSize(topicContent, 180);
      contentLines.forEach((line) => {
        doc.text(15, y, line); // left-align
        y += 6;
      });

      y += 4;

      if (y > maxY - 20) {
        doc.addPage();
        y = 10;
      }
    }

    doc.save("PracticeSet.pdf");
  };

  return (
    <button
      type="button"
      onClick={generatePdf}
      className="text-white bg-gradient-to-r from-cyan-500 to-blue-500 hover:bg-gradient-to-bl focus:ring-4 focus:outline-none focus:ring-cyan-300 dark:focus:ring-cyan-800 font-medium rounded-lg text-sm px-5 py-2.5 text-center"
    >
      Download Pdf
    </button>
  );
};

export { GenerateButton, DownloadPdfButton, DeleteButton };