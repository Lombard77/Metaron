import { useState, useEffect } from "react";
import { Menu } from "lucide-react";
import CoachingGoalSetup from "./CoachingGoalSetup";
import axios from "axios";
import StatusDisplay from "./StatusDisplay";

export default function Dashboard() {
  const [goals, setGoals] = useState([]);
  const [selectedGoal, setSelectedGoal] = useState(null);
  const [mode, setMode] = useState("home");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [showProfileMenu, setShowProfileMenu] = useState(false);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [errorMessage, setErrorMessage] = useState("");
  const [showConfirmDelete, setShowConfirmDelete] = useState(false);
  const [statusMessage, setStatusMessage] = useState("");

//  useEffect(() => {
//  if (
//    mode === "preview" &&
//    statusMessage &&
//    !statusMessage.includes("Embedding complete")
//  ) {
//    const timer = setTimeout(() => {
//      setStatusMessage("");
//    }, 5000);
//    return () => clearTimeout(timer);
//  }
//}, [mode, statusMessage]);


  const handleLogout = () => {
    localStorage.clear();
    window.location.reload();
  };

  const handleAsk = async () => {
  try {
    const payload = {
      email: localStorage.getItem("user_id"),
      goal_id: selectedGoal.goal_id,
      question,
      provider: selectedGoal.provider || "Open Source",
      api_key: selectedGoal.api_key || "",
      model_name: "gpt-3.5"
    };

    const res = await axios.post("http://localhost:8000/ask", payload);
    setAnswer(res.data.answer);
  } catch (err) {
    console.error("❌ Ask error", err);
    setAnswer("⚠️ Something went wrong.");
  }
};



  useEffect(() => {
    const userId = localStorage.getItem("user_id");
    if (!userId) {
      setErrorMessage("⚠️ You are not logged in. Please log in first.");
      return;
    }

    axios
      .get(`http://localhost:8000/goals?user_id=${userId}`)
      .then((res) => {
        setGoals(res.data.goals || []);
      })
      .catch((err) => {
        console.error("Failed to fetch goals:", err);
        setErrorMessage("⚠️ Unable to load goals. Please try again later.");
        setGoals([]);
      });
  }, []);

  useEffect(() => {
    console.log("🔁 [Dashboard] statusMessage changed to:", statusMessage);
  }, [statusMessage]);

  const handleCreateNewGoal = () => {
    setMode("create");
    setSelectedGoal(null);
  };

  const handleSelectGoal = (goal) => {
    setSelectedGoal(goal);
    setMode("preview");
      // ✅ Add this line to persist goal_id
  localStorage.setItem("selectedGoalId", goal.goal_id);
  };

  const handleGoalCreated = (goal) => {
    setGoals((prev) => [...prev, goal]);
    setSelectedGoal(goal);
    setMode("preview");
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {sidebarOpen ? (
        <div className="w-64 bg-white border-r border-gray-200 p-4 text-sm relative">
          <button
            className="absolute top-4 right-4 text-gray-500 hover:text-blue-500 transition"
            onClick={() => setSidebarOpen(false)}
            title="Collapse"
          >
            ✕
          </button>

          <div className="mb-6 pl-1">
            <img src="/logo.png" alt="Metatron Logo" className="w-16" />
          </div>

          <h3 className="font-semibold text-gray-600 mb-2 uppercase text-xs">Your Coaching Goals</h3>
          <button
            onClick={handleCreateNewGoal}
            className="mt-4 w-full py-2 px-4 bg-blue-600 text-white rounded-full hover:bg-blue-700 text-sm"
          >
            New Coaching Goal
          </button>
          <ul className="space-y-2">
            {goals.map((goal, index) => (
              <li
                key={`${goal.goal_id || goal.title || index}-${index}`}
                className="cursor-pointer px-3 py-2 rounded-lg transition hover:bg-blue-100"
                onClick={() => {
                  setSelectedGoal(goal);
                  setMode("preview");
                }}
              >
                {goal.title}
              </li>
            ))}
          </ul>



          <div className="mt-8 text-xs text-gray-400 text-center">Metatron • View plans</div>
        </div>
      ) : (
        <div className="w-10 bg-transparent p-2">
          <button
            className="text-gray-500 hover:text-blue-500"
            onClick={() => setSidebarOpen(true)}
            title="Open Menu"
          >
            <Menu size={24} />
          </button>
        </div>
      )}

      <div className="flex-1 overflow-y-auto">
        <div className="flex justify-between items-center gap-4 p-6 border-b border-gray-200 bg-white">
          <div>
            <h1 className="text-2xl font-bold text-gray-800">Metatron</h1>
            <p className="text-sm text-gray-500">A Guiding Light in the Ocean of Knowledge</p>
          </div>

          <div className="relative">
            <button
              className="text-sm font-medium text-gray-700 bg-gray-100 rounded-full px-3 py-1 hover:bg-gray-200"
              onClick={() => setShowProfileMenu(!showProfileMenu)}
            >
              👤 Profile
            </button>
            {showProfileMenu && (
              <div className="absolute right-0 mt-2 w-40 bg-white border rounded-md shadow-md z-10">
                <button
                  className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
                  onClick={handleLogout}
                >
                  Log Out
                </button>
              </div>
            )}
          </div>
        </div>

        {errorMessage && (
          <div className="fixed top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 bg-red-100 text-red-800 p-4 rounded shadow-md z-50 text-center w-[90%] max-w-md">
            <div>{errorMessage}</div>
            <div className="mt-3">
              <button
                onClick={() => setErrorMessage("")}
                className="bg-red-600 text-white px-4 py-1 rounded hover:bg-red-700"
              >
                OK
              </button>
            </div>
          </div>
        )}

        {showConfirmDelete && (
          <div className="fixed inset-0 flex items-center justify-center bg-black bg-opacity-40 z-50">
            <div className="bg-white p-6 rounded shadow-md text-center w-[90%] max-w-md">
              <h2 className="text-lg font-bold text-gray-800 mb-4">⚠️ Confirm Deletion</h2>
              <p className="text-gray-700 mb-6">
                Are you sure you want to delete this coaching goal?<br />
                This action is permanent and will remove all associated history.
              </p>
              <div className="flex justify-center gap-4">
                <button
                  onClick={async () => {
                    try {
                      const userId = localStorage.getItem("user_id");
                      await axios.post("http://localhost:8000/delete-goal", {
                        goal_id: selectedGoal.goal_id,
                      });
                      setGoals(goals.filter((g) => g.goal_id !== selectedGoal.goal_id));
                      setSelectedGoal(null);
                      setMode("home");
                      setShowConfirmDelete(false);
                    } catch (err) {
                      console.error("Failed to delete goal:", err);
                      setErrorMessage("❌ Failed to delete goal. Please try again.");
                      setShowConfirmDelete(false);
                    }
                  }}
                  className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
                >
                  Yes, Delete
                </button>
                <button
                  onClick={() => setShowConfirmDelete(false)}
                  className="bg-gray-300 text-gray-800 px-4 py-2 rounded hover:bg-gray-400"
                >
                  Cancel
                </button>
              </div>
            </div>
          </div>
        )}

        <div className="p-10">
          {mode === "home" && (
            <div className="text-gray-500 text-lg mt-10">
              Please select or create a coaching goal to begin.
            </div>
          )}

          {(mode === "create" || mode === "edit") && (
            <>
              <CoachingGoalSetup
                goal={mode === "edit" ? selectedGoal : null}
                onGoalCreated={handleGoalCreated}
                onCancel={() => setMode(mode === "edit" ? "preview" : "home")}
                setStatusMessage={setStatusMessage}
                statusMessage={statusMessage} // ✅ also pass this down
              />
            </>
          )}


          {mode === "preview" && selectedGoal && (
            <div>
              <h2 className="text-xl font-semibold mb-4">{selectedGoal.title}</h2>
              <p className="text-gray-700 mb-4">{selectedGoal.description || "No description provided."}</p>
              <div className="flex gap-4">
                <button
                  onClick={() => setMode("edit")}
                  className="bg-yellow-500 text-white px-4 py-2 rounded hover:bg-yellow-600"
                >
                  Edit Goal
                </button>
                <button
                  onClick={async () => {
                    const userId = localStorage.getItem("user_id");
                    if (!userId) {
                      setErrorMessage("⚠️ You are not logged in.");
                      return;
                    }
                    try {
                      await axios.post("http://localhost:8000/start-session", {
                        goal_id: selectedGoal.goal_id,
                      });
                      setMode("chat");
                    } catch (err) {
                      console.error("Error starting session:", err);
                      alert("Failed to start session.");
                    }
                  }}
                  className="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700"
                >
                  Start Session
                </button>

                <button
                  
                  
                  onClick={() => {
                    const userId = localStorage.getItem("user_id");
                    if (!userId) {
                      setErrorMessage("⚠️ You are not logged in.");
                      return;
                    }
                    setShowConfirmDelete(true); // Show the modal instead of using window.confirm
                  }}
                  className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
                >
                  Delete Goal
                </button>
              </div>

            </div>
          )}


          {mode === "chat" && selectedGoal && (
            <div className="max-w-2xl mx-auto p-6 bg-white rounded shadow">
              <h2 className="text-xl font-semibold mb-4">📘 Session Started</h2>
              <p className="text-gray-700 mb-6">
                You're now in a session for <strong>{selectedGoal.title}</strong>. Ask a question below.
              </p>

              <label className="block mb-1 text-sm font-medium text-gray-700">Ask a question:</label>
              <input
                type="text"
                className="w-full p-2 border rounded mb-2"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") handleAsk();
                }}
              />
              <button
                onClick={handleAsk}
                className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
              >
                Submit
              </button>

              {answer && (
                <div className="mt-4 bg-gray-100 p-4 rounded text-sm text-gray-800">
                  <strong>Answer:</strong> {answer}
                </div>
              )}
            </div>
          )}


        </div>
      </div>
    </div>
  );
}
