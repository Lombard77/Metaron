import { useState } from "react";
import LoginCard from "./components/LoginCard";
import Dashboard from "./components/Dashboard";

function App() {
  const [isLoggedIn, setIsLoggedIn] = useState(false);

  return isLoggedIn ? (
    <Dashboard />
  ) : (
    <LoginCard setIsLoggedIn={setIsLoggedIn} />
  );
}

export default App;
