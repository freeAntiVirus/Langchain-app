import React from "react";

const QuestionNumberSlider = ({ value, onChange }) => {
  return (
    <div className="relative mb-6">
      <label htmlFor="question-range-input" className="sr-only">
        Question Count
      </label>
      <input
        id="question-range-input"
        type="range"
        min="10"
        max="100"
        step="10"
        value={value}
        onChange={onChange}
        className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer dark:bg-gray-700"
      />
      {/* Labels */}
      <div className="flex justify-between text-sm text-gray-500 dark:text-gray-400 mt-2 px-1">
        <span>10</span>
        <span>20</span>
        <span>50</span>
        <span>100</span>
      </div>
    </div>
  );
};

export default QuestionNumberSlider;