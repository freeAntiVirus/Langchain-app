import React, { useState, useRef, useEffect } from "react";

function DropdownCheckbox({ label, topics, selected, onSelectionChange }) {
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef(null);

  // Close on outside click
  useEffect(() => {
    const handle = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setIsOpen(false);
    };
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, []);

  const toggle = (topic) => {
    const next = selected.includes(topic)
      ? selected.filter((t) => t !== topic)
      : [...selected, topic];
    onSelectionChange(next);
  };

  const toggleDropdown = () => {
    setIsOpen((prev) => !prev);
  };

  return (
    <div className="relative inline-block text-left" ref={ref}>
       <button
          onClick={toggleDropdown}
          className="text-white bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:outline-none focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center inline-flex items-center dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800"
          type="button"
        >
          Select Topic
          <svg
            className="w-2.5 h-2.5 ms-3"
            aria-hidden="true"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 10 6"
          >
            <path
              stroke="currentColor"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              d="m1 1 4 4 4-4"
            />
          </svg>
        </button>

      {isOpen && (
        <div className="absolute z-10 mt-2 w-96 max-h-80 overflow-y-auto rounded-lg bg-white shadow-sm ring-1 ring-black/5">
          <ul className="p-3 space-y-2 text-sm text-gray-800">
            {topics?.length === 0 && (
              <li className="px-2 py-1 text-gray-500">No topics available</li>
            )}
            {topics?.map((topic, idx) => {
              const id = `topic-${idx}`;
              const checked = selected.includes(topic);
              return (
                <li key={id} className="flex items-center gap-2">
                  <input
                    id={id}
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggle(topic)}
                    className="h-4 w-4 rounded-sm border-gray-300 text-indigo-600 focus:ring-indigo-500"
                  />
                  <label htmlFor={id} className="cursor-pointer select-none text-sm">
                    {topic}
                  </label>
                </li>
              );
            })}
          </ul>
          {selected?.length > 0 && (
            <div className="flex items-center justify-between border-t px-3 py-2 text-xs text-gray-600">
              <span>{selected?.length} selected</span>
              <button
                type="button"
                className="rounded bg-gray-100 px-2 py-1 hover:bg-gray-200"
                onClick={() => onSelectionChange([])}
              >
                Clear
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ChevronDownIcon() {
  return (
    <svg
      className="h-3 w-3"
      xmlns="http://www.w3.org/2000/svg"
      viewBox="0 0 10 6"
      fill="none"
      aria-hidden="true"
    >
      <path d="M1 1l4 4 4-4" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export default DropdownCheckbox;