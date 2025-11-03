import React, { useState, useRef, useEffect } from "react";

function DropdownMenu({ label, items, value, onChange }) {
  const [isOpen, setIsOpen] = useState(false);
  const ref = useRef(null);

  console.log("DropdownMenu props:", { label, items, value });
  // Close on outside click
  useEffect(() => {
    const handle = (e) => {
      if (ref.current && !ref.current.contains(e.target)) setIsOpen(false);
    };
    document.addEventListener("mousedown", handle);
    return () => document.removeEventListener("mousedown", handle);
  }, []);

  const toggleDropdown = () => setIsOpen((prev) => !prev);


  return (
    <div className="relative inline-block text-left" ref={ref}>
       <button
        onClick={toggleDropdown}
        className="text-white bg-blue-700 hover:bg-blue-800 focus:ring-4 focus:outline-none focus:ring-blue-300 font-medium rounded-lg text-sm px-5 py-2.5 text-center inline-flex items-center dark:bg-blue-600 dark:hover:bg-blue-700 dark:focus:ring-blue-800"
        type="button"
      >
        Select Subject
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
        <div className="absolute z-10 mt-2 w-56 rounded-lg bg-white shadow-sm ring-1 ring-black/5">
          <ul
            role="listbox"
            aria-label={label}
            className="max-h-64 overflow-y-auto py-2 text-sm text-gray-800"
          >
            {items?.map((item) => (
              <li key={item}>
                <button
                  type="button"
                  role="option"
                  aria-selected={item === value}
                  onClick={() => {
                    onChange(item);
                    setIsOpen(false);
                  }}
                  className={`block w-full px-4 py-2 text-left hover:bg-gray-100 ${
                    item === value ? "font-semibold" : ""
                  }`}
                >
                  {item}
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default DropdownMenu
