import "./App.css";
import NavBar from "./components/NavBar"; // Adjust path if NavBar is in a different folder
import Home from "./pages/Home"; // These pages must exist
import ClassifyResources from "./pages/ClassifyResources"; // Adjust path if needed
import CreatePracticeSet from "./pages/CreatePracticeSet"; // Adjust path if needed
import Generate from "./pages/Generate"; // Adjust path if neede
import { Routes, Route } from "react-router-dom";
import { BrowserRouter as Router } from 'react-router-dom';


function App() {
  return (
    <Router>
      <NavBar />
      <div className="p-6">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/classifyResources" element={<ClassifyResources />} />
          <Route path="/practice" element={<CreatePracticeSet />} />
          <Route path="/generate" element={<Generate />} />
          {/* Add more routes as needed */}
        </Routes>
      </div>
    </Router>
  );
  
}

export default App;
