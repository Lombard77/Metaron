import { useState, useEffect } from "react";
import axios from "axios";
import StatusDisplay from "./StatusDisplay";
import { flushSync } from "react-dom";


export default function CoachingGoalSetup({
  onGoalCreated,
  onCancel,
  goal = null,
  setStatusMessage,
  statusMessage              // ✅ Add this line to receive the prop
}) {
  const [goalName, setGoalName] = useState(goal?.title || "");
  const [intent, setIntent] = useState(goal?.intent || "Study");
  const [timeframe, setTimeframe] = useState(goal?.timeframe || "14 days");
  const [description, setDescription] = useState(goal?.description || "");
  const [provider, setProvider] = useState(goal?.provider || "Open Source");
  const [apiKey, setApiKey] = useState("");
  const [files, setFiles] = useState([]);
  const [selectedFiles, setSelectedFiles] = useState([]);

  const [existingFiles, setExistingFiles] = useState(
    (goal?.files || []).map((f) =>
      typeof f === "string" ? { name: f, size: 0 } : f
    )
  );

  const [removedFiles, setRemovedFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showConfirm, setShowConfirm] = useState(false);
  const [showAbortConfirm, setShowAbortConfirm] = useState(false);
  

  const [buttonLabel, setButtonLabel] = useState(
    goal ? "💾 Save Changes" : "🚀 Create Coaching Goal"
  );
  const [jobId, setJobId] = useState(null);

  const [originalState] = useState({
    title: goal?.title || "",
    intent: goal?.intent || "Study",
    timeframe: goal?.timeframe || "14 days",
    description: goal?.description || "",
    provider: goal?.provider || "Open Source"
  });

  const isUnchanged =
    goal &&
    goalName === originalState.title &&
    intent === originalState.intent &&
    timeframe === originalState.timeframe &&
    description === originalState.description &&
    provider === originalState.provider &&
    files.length === 0 &&
    removedFiles.length === 0;

  const handleFileChange = (e) => {
    const newFiles = Array.from(e.target.files);
    setSelectedFiles((prev) => [...prev, ...newFiles]);
    setFiles((prev) => [...prev, ...newFiles]);
  };
  const handleRemoveExistingFile = (filename) =>
    setRemovedFiles((prev) => [...prev, filename]);

    const handleCreateGoal = async () => {
    const userId = localStorage.getItem("user_id");
    if (!userId) {
      setStatusMessage("❌ You are not logged in. Please log in first.");
      return;
    }

    if (!goalName || (!goal && files.length === 0 && existingFiles.length === 0)) {
      setStatusMessage("❌ Please provide a goal name and at least one file.");
      return;
    }

    const remainingFiles = existingFiles.filter(f => !removedFiles.includes(f.name));
    const formData = new FormData();
    formData.append("user_id", userId);
    formData.append("goal_name", goalName);
    formData.append("intent", intent);
    formData.append("timeframe", timeframe);
    formData.append("description", description);
    formData.append("provider", provider);
    if (provider === "OpenAI") formData.append("api_key", apiKey);

    files.forEach((file) => formData.append("files", file));
    formData.append("existing_files", JSON.stringify(remainingFiles.map(f => f.name)));

    setJobId(null);                   // ✅ Clear any existing job tracking
    setStatusMessage("");            // ✅ Reset status text
    setLoading(true);
    console.log("⏳ Upload triggered. Spinner active.");
    setStatusMessage(getLabelForStatus("uploading"));
    setButtonLabel(getLabelForStatus("uploading"));


    const rotatingMessages = [
      "⏳ Creating your goal...",
      "📡 Uploading & reading files...",
      "📖 Parsing data (~3–5 mins per MB)...",
      "🧠 Embedding knowledge...",
      "🔁 Still working – almost there!"
    ];
    let msgIndex = 0;
    const buttonTimer = setInterval(() => {
      setButtonLabel(rotatingMessages[msgIndex]);
      msgIndex = (msgIndex + 1) % rotatingMessages.length;
    }, 3000);

    try {
      const res = await axios.post("http://localhost:8000/upload-kb", formData);
      if (res.data.job_id) {
        console.log("✅ Polling started with job ID:", res.data.job_id);
        setJobId(res.data.job_id);
        clearInterval(buttonTimer); // 🛑 Stop rotating once polling begins
        setTimeout(() => {
          startPolling(res.data.job_id);
        }, 4000);
              } else if (res.data.status === "ok") {
        setStatusMessage("✅ Coaching Goal created!");
        setButtonLabel("✅ Goal Created!");
        setLoading(false);
        clearInterval(buttonTimer); // 🛑 Stop rotating
      } else {
        showMessage("❌ Unknown response from server.");
        setButtonLabel("❌ Failed");
        setLoading(false);
        clearInterval(buttonTimer); // 🛑 Stop rotating
      }

      if (onGoalCreated) {
        onGoalCreated({
          id: Date.now(),
          title: goalName,
          intent,
          timeframe,
          description,
          provider,
          files: [...remainingFiles, ...files.map(f => ({ name: f.name, size: f.size }))]
        });
      }
    } catch (err) {
      const backendMsg = err?.response?.data?.detail;
      showMessage(`❌ ${backendMsg || "Upload failed. Please try a smaller or simpler file."}`);
      setButtonLabel("❌ Failed");
      console.error("Upload error:", err);
      setLoading(false);
      clearInterval(buttonTimer); // 🛑 Stop rotating
    }

  };

  const getLabelForStatus = (status) => {
  switch (status) {
    case "uploading":
      return "📦 Uploading files...";
    case "parsing":
      return "🔍 Parsing text...";
    case "embedding":
      return "🧠 Embedding content...";
    case "finalizing":
      return "📊 Finalizing...";
    case "complete":
      return "✅ Embedding complete!";
    default:
      return "⏳ Working...";
  }
};


const startPolling = (jobId) => {
  let attempts = 0;
  const poll = async () => {
    try {
      console.log("📡 Polling for job status...");
      const res = await axios.get(`http://localhost:8000/job-status?job_id=${jobId}`);
      const status = res.data.status;

      if (!status || status === "waiting") {
        console.log("⏳ Job not ready yet...");
        setTimeout(poll, 4000);
        return;
      }

      const label = getLabelForStatus(status);
      console.log("📢 Received status:", status, "→", label);

      // ✅ Force a visible UI update even if label string is the same
      flushSync(() => {
        setStatusMessage("");         // Clear first
      });
      flushSync(() => {
        setStatusMessage(label);     // Then re-apply new label
      });
      setButtonLabel(label);


      if (["complete", "error", "failed"].includes(status)) {
        return; // ✅ Stop polling on terminal status
      }

      setTimeout(poll, 5000); // 🔁 Poll every 5 sec
    } catch (err) {
      console.error("❌ Polling failed:", err);
      if (++attempts < 3) {
        setTimeout(poll, 5000);
      } else {
        setStatusMessage("❌ Lost connection to job status.");
        setLoading(false);
      }
    }
  };

  poll();
};




  const handleAbort = () => {
    setShowAbortConfirm(true); // ✅ This triggers the custom modal instead
  };


  return (
    <div className="max-w-xl mx-auto p-6 bg-white rounded-lg shadow-md">
      <h2 className="text-xl font-bold mb-4">
        {goal ? "Edit Coaching Goal" : "Create a Coaching Goal"}
      </h2>

      {loading && (
        <div className="text-center my-4 space-y-1">
          {/* Always show this static line */}
          <div className="text-blue-500 text-sm animate-pulse">
            ⏳ Preparing your goal. This may take a while...
          </div>

          {/* Only show dynamic status below if available */}
          {statusMessage && (
            <div className="text-gray-600 text-sm">
              <StatusDisplay message={statusMessage} />
            </div>
          )}
        </div>
      )}



      <label className="block mb-2">Goal Name</label>
      <input
        type="text"
        value={goalName}
        onChange={(e) => setGoalName(e.target.value)}
        className="w-full mb-4 p-2 border rounded"
        disabled={loading}
      />

      <label className="block mb-2">Select AI Engine</label>
      <select
        value={provider}
        onChange={(e) => setProvider(e.target.value)}
        className="w-full mb-2 p-2 border rounded"
        disabled={loading}
      >
        <option value="Open Source">Open Source (Free, slower)</option>
        <option value="OpenAI">OpenAI (Faster, requires API key)</option>
      </select>

      {provider === "OpenAI" && (
        <div className="mb-4">
          <p className="text-sm text-gray-600 mb-1">OpenAI usage may incur additional costs. Enter your API key below:</p>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            className="w-full p-2 border rounded"
            disabled={loading}
          />
        </div>
      )}

      <label className="block mb-2">Upload Files</label>
      <input
        type="file"
        multiple
        onChange={handleFileChange}
        className="hidden"
        id="file-upload"
        disabled={loading}
      />
      <label htmlFor="file-upload" className="inline-block mb-2 px-4 py-2 bg-blue-100 text-blue-700 rounded cursor-pointer hover:bg-blue-200">
        📁 Choose Files
      </label>

      {selectedFiles.map((file, index) => (
        <div key={index} className="flex justify-between text-xs text-gray-600 mb-1">
          <span>{file.name} — {(file.size / (1024 * 1024)).toFixed(2)} MB</span>
          <button
            type="button"
            className="text-red-500 ml-2"
            onClick={() => {
              const updatedFiles = selectedFiles.filter((_, i) => i !== index);
              setSelectedFiles(updatedFiles);
              setFiles(updatedFiles);  // keep this in sync
            }}
          >
            ❌
          </button>
        </div>
      ))}


      {existingFiles
        .filter(file => !removedFiles.includes(file.name))
        .map(file => (
          <div key={file.name} className="text-xs text-gray-700 ml-1 mb-1 flex justify-between">
            <span>{file.name} — {(file.size / (1024 * 1024)).toFixed(2)} MB</span>
            <button
              onClick={() => handleRemoveExistingFile(file.name)}
              className="text-red-500 text-xs hover:underline"
            >
              Remove
            </button>
          </div>
        ))}


      <label className="block mb-2">Intent</label>
      <select
        value={intent}
        onChange={(e) => setIntent(e.target.value)}
        className="w-full mb-4 p-2 border rounded"
        disabled={loading}
      >
        <option>Study</option>
        <option>Test</option>
        <option>Assignment</option>
      </select>

      <label className="block mb-2">Timeframe</label>
      <select
        value={timeframe}
        onChange={(e) => setTimeframe(e.target.value)}
        className="w-full mb-4 p-2 border rounded"
        disabled={loading}
      >
        <option>7 days</option>
        <option>14 days</option>
        <option>30 days</option>
        <option>Custom</option>
      </select>

      <label className="block mb-2">Goal Description</label>
      <textarea
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        className="w-full mb-4 p-2 border rounded"
        rows={3}
        disabled={loading}
      ></textarea>

      {jobId && (
        <div className="text-sm text-center text-gray-700 mb-4 border p-3 rounded bg-gray-50 shadow-inner">
          <div className="mb-1">
            📡 <strong>Job ID:</strong> {jobId}
          </div>
        </div>
      )}

      <div className="flex gap-2">
        <button
          onClick={() => {
            if (isUnchanged) {
              setStatusMessage("⚠️ No changes detected.");
              return;
            }
            if (goal) {
              setShowConfirm(true); // <-- trigger modal instead
              return;
            }
            handleCreateGoal();
          }}
          disabled={loading}
          className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
        >
          {buttonLabel}
        </button>

        <button
          onClick={handleAbort}
          disabled={loading && !jobId}
          className="w-32 bg-gray-300 text-gray-800 py-2 rounded hover:bg-gray-400"
        >
          ✖ Cancel
        </button>
      {showConfirm && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={() => setShowConfirm(false)}
        >
          <div
            className="bg-white p-6 rounded-lg shadow-lg max-w-sm w-full"
            onClick={(e) => e.stopPropagation()} // prevents background click from closing
          >
            <h3 className="text-lg font-semibold mb-3">⚠️ Overwrite Coaching Goal?</h3>
            <p className="text-sm text-gray-700 mb-4">
              Saving will overwrite your previous plan and reset progress. Continue?
            </p>
            <div className="flex justify-end gap-2">
              <button
                className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
                onClick={() => setShowConfirm(false)}
              >
                Cancel
              </button>
              <button
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
                onClick={() => {
                  setShowConfirm(false);
                  handleCreateGoal();
                }}
              >
                Yes, Save
              </button>
            </div>
          </div>
        </div>
      )}

      {showAbortConfirm && (
        <div
          className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50"
          onClick={() => setShowAbortConfirm(false)}
        >
          <div
            className="bg-white p-6 rounded-lg shadow-lg max-w-sm w-full"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold mb-3">⚠️ Abort Coaching Goal Setup?</h3>
            <p className="text-sm text-gray-700 mb-4">
              Are you sure you want to discard all changes?
            </p>
            <div className="flex justify-end gap-2">
              <button
                className="px-4 py-2 bg-gray-200 rounded hover:bg-gray-300"
                onClick={() => setShowAbortConfirm(false)}
              >
                Cancel
              </button>
              <button
                className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
                onClick={() => {
                  setShowAbortConfirm(false);
                  if (onCancel) onCancel();
                }}
              >
                Yes, Abort
              </button>
            </div>
          </div>
        </div>
      )}


  
      </div>
    </div>
  );
}
