import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import { Button } from "@/components/ui/button";
import Home from "./pages/Home";
import Chat from "./pages/Chat";
import MyParlays from "./pages/MyParlays";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col items-center justify-center bg-gray-950 text-white gap-8 px-4 py-10">
        {/* App Header */}
        <h1 className="text-4xl font-bold tracking-tight">
          🧠 AI Parlay Assistant
        </h1>

        {/* Navigation Buttons */}
        <div className="flex gap-4">
          <Link to="/">
            <Button
              className="cursor-pointer hover:scale-105 transition-transform"
              variant="secondary"
            >
              🏠 Home
            </Button>
          </Link>
          <Link to="/chat">
            <Button className="cursor-pointer hover:scale-105 transition-transform">
              💬 Open Chat
            </Button>
          </Link>
          <Link to="/my-parlays">
            <Button
            variant="outline"
            className="cursor-pointer hover:scale-105 transition-transform text-gray-900">
            📜 My Parlays
          </Button>
          </Link>
        </div>

        {/* Page Routes */}
        <div className="w-full max-w-4xl mt-8">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/my-parlays" element={<MyParlays />} /> {/* ✅ Added */}
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  );
}
