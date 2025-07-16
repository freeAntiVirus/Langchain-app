import React from "react";

const HomepageHero = () => {
  return (
    <div className="max-w-[85rem] mx-auto px-4 sm:px-6 lg:px-8">
      <div className="grid md:grid-cols-2 gap-4 md:gap-8 xl:gap-20 md:items-center">
        {/* Left Column */}
        <div>
          <h1 className="block text-3xl font-bold text-gray-800 sm:text-4xl lg:text-6xl lg:leading-tight dark:text-white">
            Start your journey with{" "}
            <span className="text-blue-600">HSCHUB</span>
          </h1>
          <p className="mt-3 text-lg text-gray-800 dark:text-neutral-400">
            Smarter HSC study starts here. HSCHub uses AI to classify, generate, and personalise exam-style questions by topic — so you can revise with purpose, not panic
          </p>

          {/* Buttons */}
          <div className="mt-7 grid gap-3 w-full sm:inline-flex">
            <a
              href="#"
              className="py-3 px-4 inline-flex justify-center items-center gap-x-2 text-sm font-medium rounded-lg border border-transparent bg-blue-600 text-white hover:bg-blue-700 focus:outline-hidden focus:bg-blue-700 disabled:opacity-50 disabled:pointer-events-none"
            >
              Get started
              <svg
                className="shrink-0 size-4"
                xmlns="http://www.w3.org/2000/svg"
                width="24"
                height="24"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="m9 18 6-6-6-6" />
              </svg>
            </a>
            <a
              href="#"
              className="py-3 px-4 inline-flex justify-center items-center gap-x-2 text-sm font-medium rounded-lg border border-gray-200 bg-white text-gray-800 shadow-2xs hover:bg-gray-50 focus:outline-hidden focus:bg-gray-50 disabled:opacity-50 disabled:pointer-events-none dark:bg-neutral-900 dark:border-neutral-700 dark:text-white dark:hover:bg-neutral-800 dark:focus:bg-neutral-800"
            >
              Contact sales team
            </a>
          </div>

         
        </div>

        {/* Right Column (Image) */}
        <div className="relative ms-4">
    <img
      src="/assets/20944386.jpg"
      alt="Descriptive text"
      className="w-full h-[80vh] object-contain mx-auto"
    />
          <div/>

          
        </div>
      </div>
    </div>
  );
};

export default HomepageHero;