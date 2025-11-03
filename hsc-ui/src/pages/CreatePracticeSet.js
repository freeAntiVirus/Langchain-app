import React, { useState } from "react";
import axios from "axios";

import SubjectTopicPicker from "../components/SubjectTopicPicker"; // ⬅️ new
import { GenerateButton, DownloadPdfButton } from "../components/Buttons";
import ScrollableTextBox from "../components/ScrollableTextbox";
import QuestionNumberSlider from "../components/Slider";

function CreatePracticeSet() {
  const [questionCount, setQuestionCount] = useState(10);
  const [subject, setSubject] = useState("Mathematics Advanced"); // ⬅️ new
  const [selectedTopics, setSelectedTopics] = useState([]);
  const [questions, setQuestions] = useState([]);
  const [visibleQuestions, setVisibleQuestions] = useState([]); // track display

  const handleGenerate = async () => {
    console.log("handleGenerate triggered");
    try {
      const res = await axios.post("http://localhost:8000/get-questions", {
        subject,               // ⬅️ optional but often useful
        topics: selectedTopics,
        count: questionCount,
      });
      console.log("Axios response:", res.data);
      const fetchedQuestions = res.data.questions || [];
      setQuestions(fetchedQuestions);
      setVisibleQuestions(fetchedQuestions); // sync both states
    } catch (err) {
      console.error("Axios failed:", err);
      setQuestions([]);
      setVisibleQuestions([]);
    }
  };


  return (
    <div className="p-6">
      <div className="flex flex-col md:flex-row gap-8">
        {/* Left Panel */}
        <div className="w-full md:w-[50%]">
          <h1 className="text-2xl font-bold mb-4">Create Practice Set</h1>
          <p className="mb-6">Select the subject and topics you want to practice.</p>

          <div className="flex flex-wrap gap-4 items-end">
            <div className="w-full">
              <h2 className="text-sm font-medium mb-1">Subject & Topics</h2>
              <SubjectTopicPicker
                initialSubject={subject}
                onChange={(s, topics) => {
                  setSubject(s);
                  setSelectedTopics(topics);
                }}
              />
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
          <ScrollableTextBox
            questions={questions}
            onQuestionsUpdate={setVisibleQuestions}
          />
          <DownloadPdfButton
            questions={visibleQuestions}
          />
        </div>
      </div>
    </div>
  );
}

export default CreatePracticeSet;