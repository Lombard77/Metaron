import { useEffect } from "react";

export default function StatusDisplay({ message }) {
  useEffect(() => {
    console.log("🟩 StatusDisplay update:", message);
  }, [message]);

  // 💥 Force always-render via key
  return (
    <div
      key={message}
      className="text-center text-blue-600 text-sm mb-4 animate-pulse"
    >
      {message}
    </div>
  );
}
