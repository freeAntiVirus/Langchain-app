import DropdownCheckbox from "../components/DropDownCheckBox";
import DropdownMenu from "../components/DropDown";
import {GenerateButton, DownloadPdfButton} from "../components/Buttons";
import ScrollableTextBox from "../components/ScrollableTextbox";
import QuestionNumberSlider from "../components/Slider";
import React, { useState } from "react";

function CreatePracticeSet() {
  const [questionCount, setQuestionCount] = useState(10);

  return (
    <div className="p-6">
      {/* Main 2-column layout */}
      <div className="flex flex-col md:flex-row gap-8">
        {/* Left Panel */}
        <div className="w-full md:w-[50%]">
          {/* Heading and description */}
          <h1 className="text-2xl font-bold mb-4">Create Practice Set</h1>
          <p className="mb-6">This is where you can create a practice set.</p>

          {/* Dropdowns and button */}
          <div className="flex flex-wrap gap-4 items-end">
            <div>
              <h2 className="text-sm font-medium mb-1">Select Subject</h2>
              <DropdownMenu />
            </div>
            <div>
              <h2 className="text-sm font-medium mb-1">Select Topics</h2>
              <DropdownCheckbox />
            </div>
          </div>

          {/* Slider */}
          <div className="mt-12">
            <h2 className="text-sm font-medium mb-2">Number of Questions</h2>
            <QuestionNumberSlider
              value={questionCount}
              onChange={(e) => setQuestionCount(parseInt(e.target.value))}
            />
            <p className="text-sm text-gray-600">Selected: {questionCount} questions</p>
          </div>

          {/* Generate button */}
          <div className="mt-12">
            <GenerateButton />
          </div>
        </div>

        {/* Right Panel: Scrollable Text Box + PDF button */}
        <div className="w-full md:w-[50%] h-full flex flex-col gap-4">
          <ScrollableTextBox />
          <DownloadPdfButton />
        </div>
      </div>
    </div>
  );
}

export default CreatePracticeSet;