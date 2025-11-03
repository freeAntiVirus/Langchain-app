import React, { useEffect, useMemo, useState } from "react";
import DropdownCheckbox from "./DropDownCheckBox";
import DropdownMenu from "./DropDown";

/**
 * Parent component wiring two dropdowns:
 * 1) Subject selector (DropdownMenu)
 * 2) Topic multi-select (DropdownCheckbox)
 *
 * Selecting a subject updates the topics shown in the topic dropdown.
 */
export default function SubjectTopicPicker({
  initialSubject = "Mathematics Advanced",
  onChange, // (subject: string, topics: string[]) => void
}) {
  const SUBJECT_TOPICS = useMemo(
    () => ({
      "Mathematics Advanced": [
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
      ],
      "Mathematics Standard": [
        // Year 11
        "MS-M1: Applications of Measurement (Year 11)",
        "M1.1: Practicalities of Measurement (Year 11)",
        "M1.2: Perimeter, Area and Volume (Year 11)",
        "M1.3: Units of Energy and Mass (Year 11)",

        "MS-M2: Working with Time (Year 11)",

        "MS-F1: Money Matters (Year 11)",
        "F1.1: Interest and Depreciation (Year 11)",
        "F1.2: Earning and Managing Money (Year 11)",
        "F1.3: Budgeting and Household Expenses (Year 11)",

        "MS-A1: Formulae and Equations (Year 11)",

        "MS-A2: Linear Relationships (Year 11)",

        "MS-S1: Data Analysis (Year 11)",
        "S1.1: Classifying and Representing Data (Year 11)",
        "S1.2: Summary Statistics (Year 11)",

        "MS-S2: Relative Frequency and Probability (Year 11)",

        // Year 12
        "MS-A4: Types of Relationships (Year 12)",
        "A4.1: Simultaneous Linear Equations (Year 12)",
        "A4.2: Non-linear Relationships (Year 12)",

        "MS-F4: Investments and Loans (Year 12)",
        "F4.1: Investments (Year 12)",
        "F4.2: Depreciation and Loans (Year 12)",

        "MS-F5: Annuities (Year 12)",

        "MS-M6: Non-right-angled Trigonometry (Year 12)",

        "MS-M7: Rates and Ratios (Year 12)",

        "MS-S4: Bivariate Data Analysis (Year 12)",

        "MS-S5: The Normal Distribution (Year 12)",

        "MS-N2: Network Concepts (Year 12)",
        "N2.1: Networks (Year 12)",
        "N2.2: Shortest Paths (Year 12)",

        "MS-N3: Critical Path Analysis (Year 12)"
    ],
    Biology: [

      "BIO-M5.1: Reproduction (Year 12)",
      "BIO-M5.2: Cell Replication (Year 12)",
      "BIO-M5.3: DNA and Polypeptide Synthesis (Year 12)",
      "BIO-M5.4: Genetic Variation (Year 12)",
      "BIO-M5.5: Inheritance Patterns in a Population (Year 12)",
      "BIO-M6.1: Mutation (Year 12)",
      "BIO-M6.2: Biotechnology (Year 12)",
      "BIO-M6.3: Genetic Technologies (Year 12)",
      "BIO-M7.1: Causes of Infectious Disease (Year 12)",
      "BIO-M7.2: Responses to Pathogens (Year 12)",
      "BIO-M7.3: Immunity (Year 12)",
      "BIO-M7.4: Prevention, Treatment and Control (Year 12)",
      "BIO-M8.1: Homeostasis (Year 12)",
      "BIO-M8.2: Causes and Effects (Year 12)",
      "BIO-M8.3: Epidemiology (Year 12)",
      "BIO-M8.4: Prevention (Year 12)",
      "BIO-M8.5: Technologies and Disorders (Year 12)",
      "BIO-WS1: Questioning and Predicting",
      "BIO-WS2: Planning Investigations",
      "BIO-WS3: Conducting Investigations",
      "BIO-WS4: Processing Data and Information",
      "BIO-WS5: Analysing Data and Information",
      "BIO-WS6: Problem Solving",
      "BIO-WS7: Communicating"

      ],
    }),
    []
  );

  const subjects = Object.keys(SUBJECT_TOPICS);
  console.log("Available subjects:", subjects);
  const [subject, setSubject] = useState(initialSubject);
  const [selectedTopics, setSelectedTopics] = useState([]);

  // When subject changes, clear topic selections (or adjust if you prefer to persist overlapping ones)
  useEffect(() => {
    setSelectedTopics([]);
  }, [subject]);

  useEffect(() => {
    onChange?.(subject, selectedTopics);
  }, [subject, selectedTopics, onChange]);
  console.log("Rendering SubjectTopicPicker", { subject, selectedTopics });

  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-start">
      <DropdownMenu
        label="Select Subject"
        items={subjects}
        value={subject}
        onChange={setSubject}
      />

      <DropdownCheckbox
        label="Select Topics"
        topics={SUBJECT_TOPICS[subject] || []}
        selected={selectedTopics}
        onSelectionChange={setSelectedTopics}
      />
    </div>
  );
}