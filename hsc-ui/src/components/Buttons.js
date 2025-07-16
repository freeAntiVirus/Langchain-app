import React from "react";

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

const DownloadPdfButton = ({ onClick }) => {
  return (
    <button
      type="button"
      onClick={onClick}
      className="text-white bg-gradient-to-r from-cyan-500 to-blue-500 hover:bg-gradient-to-bl focus:ring-4 focus:outline-none focus:ring-cyan-300 dark:focus:ring-cyan-800 font-medium rounded-lg text-sm px-5 py-2.5 text-center"
    >
      Download Pdf
    </button>
  );
};

export {GenerateButton, DownloadPdfButton};