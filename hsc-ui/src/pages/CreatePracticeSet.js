import DropdownCheckbox from "../components/DropDownCheckBox";
import DropdownMenu from "../components/DropDown";
import { GenerateButton, DownloadPdfButton } from "../components/Buttons";
import ScrollableTextBox from "../components/ScrollableTextbox";
import QuestionNumberSlider from "../components/Slider";
import React, { useState } from "react";
import axios from "axios";

function CreatePracticeSet() {
  const [questionCount, setQuestionCount] = useState(10);
  const [selectedTopics, setSelectedTopics] = useState([]);
  const [questions, setQuestions] = useState([]);

  const handleGenerate = async () => {
    console.log("handleGenerate triggered");
    try {
      const res = await axios.post("http://localhost:8000/get-questions", {
        topics: selectedTopics,
        count: questionCount,
      });
      console.log("Axios response:", res.data);
      setQuestions(res.data.questions || []);
    } catch (err) {
      console.error("Axios failed:", err);
      setQuestions([]);
    }
  };

  return (
    <div className="p-6">
      <div className="flex flex-col md:flex-row gap-8">
        {/* Left Panel */}
        <div className="w-full md:w-[50%]">
          <h1 className="text-2xl font-bold mb-4">Create Practice Set</h1>
          <p className="mb-6">This is where you can create a practice set.</p>

          <div className="flex flex-wrap gap-4 items-end">
            <div>
              <h2 className="text-sm font-medium mb-1">Select Subject</h2>
              <DropdownMenu />
            </div>
            <div>
              <h2 className="text-sm font-medium mb-1">Select Topics</h2>
              <DropdownCheckbox onSelectionChange={setSelectedTopics} />
            </div>
          </div>

          <div className="mt-12">
            <h2 className="text-sm font-medium mb-2">Number of Questions</h2>
            <QuestionNumberSlider
              value={questionCount}
              onChange={(e) => setQuestionCount(parseInt(e.target.value))}
            />
            <p className="text-sm text-gray-600">Selected: {questionCount} questions</p>
          </div>

          <div className="mt-12">
            <GenerateButton onClick={handleGenerate} />
          </div>
        </div>

        {/* Right Panel */}
        <div className="w-full md:w-[50%] h-full flex flex-col gap-4">
          <ScrollableTextBox questions={questions} />
          <DownloadPdfButton />
        </div>
      </div>
    </div>
  );
}

export default CreatePracticeSet;
