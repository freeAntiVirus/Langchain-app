import React, { useState, useRef, useEffect } from "react";

const DropdownCheckbox = ({ onSelectionChange }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [selectedTopics, setSelectedTopics] = useState([]);
  const dropdownRef = useRef(null);

  const toggleDropdown = () => setIsOpen((prev) => !prev);

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const topics = [
    "MA-C1: Introduction to Differentiation (Year 11)",
    "MA-C2: Differential Calculus (Year 12)",
    "MA-C3: Applications of Differentiation (Year 12)",
    "MA-C4: Integral Calculus (Year 12)",
    "MA-E1: Logarithms and Exponentials (Year 11)",
    "MA-F1: Working with Functions (Year 11)",
    "MA-F2: Graphing Techniques (Year 12)",
    "MA-S1: Probability and Discrete Probability Distributions (Year 11)",
    "MA-S2: Descriptive Statistics and Bivariate Data Analysis (Year 12)",
    "MA-S3: Random Variables (Year 12)",
    "MA-T1: Trigonometry and Measure of Angles (Year 11)",
    "MA-T2: Trigonometric Functions and Identities (Year 11)",
    "MA-T3: Trigonometric Functions and Graphs (Year 12)",
    "MA-M1: Modelling Financial Situations (Year 12)",
  ];

  const handleCheckboxChange = (topic) => {
    const updated = selectedTopics.includes(topic)
      ? selectedTopics.filter((t) => t !== topic)
      : [...selectedTopics, topic];

    setSelectedTopics(updated);
    onSelectionChange(updated); // Pass selection up
  };

  return (
    <div className="relative inline-block text-left" ref={dropdownRef}>
      <button
        onClick={toggleDropdown}
        className="text-white bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:outline-none focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center inline-flex items-center"
        type="button"
      >
        Dropdown checkbox
        <svg className="w-2.5 h-2.5 ms-3" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 10 6">
          <path stroke="currentColor" strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="m1 1 4 4 4-4" />
        </svg>
      </button>

      {isOpen && (
        <div className="absolute z-10 mt-2 w-96 max-h-80 overflow-y-auto bg-white divide-y divide-gray-100 rounded-lg shadow-sm">
          <ul className="p-3 space-y-3 text-sm text-gray-700">
            {topics.map((topic, index) => {
              const id = `checkbox-topic-${index}`;
              return (
                <li key={id}>
                  <div className="flex items-center">
                    <input
                      id={id}
                      type="checkbox"
                      checked={selectedTopics.includes(topic)}
                      onChange={() => handleCheckboxChange(topic)}
                      className="w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded-sm"
                    />
                    <label htmlFor={id} className="ms-2 text-sm font-medium text-gray-900">
                      {topic}
                    </label>
                  </div>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
};

export default DropdownCheckbox;
