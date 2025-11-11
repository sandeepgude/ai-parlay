import { BrowserRouter, Routes, Route, Link } from "react-router-dom";
import Chat from "./components/Chat";
import { Button } from "@/components/ui/button";

export default function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen flex flex-col items-center justify-center bg-gray-950 text-white gap-4">
        <h1 className="text-4xl font-bold">AI Parlay Assistant 💬</h1>

        <div className="flex gap-4">
          <Link to="/">
            <Button variant="secondary">Home</Button>
          </Link>
          <Link to="/chat">
            <Button>Open Chat</Button>
          </Link>
        </div>

        <Routes>
          <Route path="/" element={<div>Welcome! Click "Open Chat" to start.</div>} />
          <Route path="/chat" element={<Chat />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}
