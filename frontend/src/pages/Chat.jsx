import { useState, useRef, useEffect } from "react";
import axiosClient from "../api/axiosClient";
import ParlayCard from "../components/ParlayCard";

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const userMsg = { sender: "user", text: input };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await axiosClient.post("/ai/parlay", { message: userMsg.text });
      console.log("🎯 API Response:", res.data);

      let botReply = res.data?.data?.raw_text
        ?.replace(/```json/g, "")
        .replace(/```/g, "")
        .trim();

      // If backend returned parsed_parlay directly, prefer that
      if (res.data?.data?.parsed_parlay) {
        setMessages((prev) => [
          ...prev,
          { sender: "bot", parlay: res.data.data.parsed_parlay },
        ]);
      } else {
        try {
          const parsed = JSON.parse(botReply);
          setMessages((prev) => [...prev, { sender: "bot", parlay: parsed }]);
        } catch {
          // Fallback: plain text reply
          const fallback = botReply || res.data?.message || "No reply received.";
          setMessages((prev) => [...prev, { sender: "bot", text: fallback }]);
        }
      }
    } catch (error) {
      console.error("❌ Error fetching parlay:", error);
      setMessages((prev) => [
        ...prev,
        { sender: "bot", text: "⚠️ Unable to generate parlay. Please try again." },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center h-screen bg-gray-50 p-4">
      <h1 className="text-2xl font-semibold mb-4">🎯 AI Parlay Assistant</h1>

      <div className="max-w-2xl w-full bg-white shadow-md rounded-xl flex flex-col p-4 overflow-y-auto flex-grow mb-4 border">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`my-2 ${m.sender === "user" ? "text-right" : "text-left"}`}
          >
            {m.sender === "bot" && m.parlay ? (
              <ParlayCard data={m.parlay} />
            ) : (
              <p
                className={`inline-block px-4 py-2 rounded-2xl ${
                  m.sender === "user"
                    ? "bg-blue-500 text-white"
                    : "bg-gray-200 text-gray-800"
                }`}
              >
                {m.text}
              </p>
            )}
          </div>
        ))}

        {loading && (
          <p className="text-gray-400 text-sm italic text-left mt-2">
            AI is building your parlay...
          </p>
        )}

        <div ref={chatEndRef} />
      </div>

      <form onSubmit={sendMessage} className="flex w-full max-w-2xl">
        <input
          className="flex-grow bg-gray-100 text-gray-900 border border-gray-300 rounded-l-xl p-3 outline-none focus:ring-2 focus:ring-blue-400"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask AI to build a parlay (e.g., 'Best NBA parlay tonight')"
        />
        <button
          type="submit"
          className="bg-blue-500 text-white px-6 rounded-r-xl hover:bg-blue-600"
          disabled={loading}
        >
          Send
        </button>
      </form>
    </div>
  );
}
