import { useEffect, useState } from "react";
import { loginUser, registerUser } from "../api";

export default function LoginCard({ setIsLoggedIn }) {
  const [isNewUser, setIsNewUser] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [ageGroup, setAgeGroup] = useState("Adult");
  const [message, setMessage] = useState("");
    // 🔄 Auto-clear error/success message after 2 seconds

  useEffect(() => {
    if (message) {
      const timeout = setTimeout(() => setMessage(""), 2000);
      return () => clearTimeout(timeout);
    }
  }, [message]);
    // ⌨️ Allow keyboard submit via Enter

  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Enter") {
        isNewUser ? handleRegister() : handleLogin();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  });

  const flashClearMessage = () => {
    setMessage("");
    return new Promise((resolve) => setTimeout(resolve, 100));
  };

  const handleLogin = async () => {
    await flashClearMessage();
    try {
      const res = await loginUser(email, password);
      setMessage("✅ " + res.message);
      localStorage.setItem("user_id", res.user_id); // ✅ FIXED: store real user_id
      setIsLoggedIn(true);
    } catch (err) {
      let friendly = "Login failed. Please check your email and password.";
      try {
        const json = JSON.parse(err.message);
        if (json.detail === "User not found") friendly = "No account found with that email.";
        if (json.detail === "Incorrect password") friendly = "That password is incorrect.";
      } catch {}
      setMessage("❌ " + friendly);
    }
  };

  const handleRegister = async () => {
    await flashClearMessage();
    try {
      const res = await registerUser({
        email,
        password,
        first_name: firstName,
        last_name: lastName,
        age_group: ageGroup,
      });
      setMessage("✅ " + res.message + " Logging in...");
      localStorage.setItem("user_id", res.user_id); // ✅ USE returned user_id
      setIsLoggedIn(true); // ✅ Skip redundant loginUser()
    } catch (err) {
      setMessage("❌ " + err.message);
    }
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100 px-4">
      <div className="w-full max-w-md p-6 bg-white rounded-lg shadow-md">
        <div className="text-center mb-4">
          <img src="/logo.png" alt="Metatron Logo" className="h-16 mx-auto mb-2" />
          <div className="text-2xl font-bold">Metatron</div>
          <div className="text-sm text-gray-600">A Guiding Light in the Ocean of Knowledge</div>
        </div>

        <label className="block mb-2">Email</label>
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full mb-4 p-2 border rounded"
          autoFocus
        />

        <label className="block mb-2">Password</label>
        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full mb-4 p-2 border rounded"
        />

        {isNewUser && (
          <>
            <label className="block mb-2">First Name</label>
            <input
              type="text"
              value={firstName}
              onChange={(e) => setFirstName(e.target.value)}
              className="w-full mb-4 p-2 border rounded"
            />

            <label className="block mb-2">Last Name</label>
            <input
              type="text"
              value={lastName}
              onChange={(e) => setLastName(e.target.value)}
              className="w-full mb-4 p-2 border rounded"
            />

            <label className="block mb-2">Age Group</label>
            <select
              value={ageGroup}
              onChange={(e) => setAgeGroup(e.target.value)}
              className="w-full mb-4 p-2 border rounded"
            >
              <option value="Child">Child</option>
              <option value="Teen">Teen</option>
              <option value="Adult">Adult</option>
              <option value="Senior">Senior</option>
            </select>
          </>
        )}

        {message && (
          <div
            className={`mb-4 p-2 rounded transition ${
              message.startsWith("✅") ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800"
            }`}
          >
            {message}
          </div>
        )}

        <button
          onClick={isNewUser ? handleRegister : handleLogin}
          className="w-full bg-blue-600 text-white py-2 rounded hover:bg-blue-700"
        >
          {isNewUser ? "Sign Up" : "Login"}
        </button>

        <p className="mt-4 text-center text-sm text-gray-600">
          {isNewUser ? "Already have an account?" : "New here?"}{" "}
          <button
            onClick={() => {
              setMessage("");
              setIsNewUser(!isNewUser);
            }}
            className="text-blue-600 hover:underline"
          >
            {isNewUser ? "Login instead" : "Create account"}
          </button>
        </p>
      </div>
    </div>
  );
}
