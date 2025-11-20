import { useState, useRef, useEffect } from "react";
import ParlayCard from "../components/ParlayCard";
import axiosClient from "../api/axiosClient";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api/v1";

const makeId = () => {
  if (typeof crypto !== "undefined" && crypto?.randomUUID) {
    return crypto.randomUUID();
  }
  return `${Date.now()}-${Math.random().toString(16).slice(2)}`;
};

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const chatEndRef = useRef(null);
  const streamAbortRef = useRef(null);

  // Auto scroll to bottom
  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };
  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      streamAbortRef.current?.abort();
    };
  }, []);

  // ============================================================
  // 🔥 STREAM REPLY (Reads text + detects FINAL JSON)
  // ============================================================
  const streamReply = async (text, botMessageId, onFinalJson) => {
    // Cancel ongoing stream
    streamAbortRef.current?.abort();
    const controller = new AbortController();
    streamAbortRef.current = controller;

    const response = await fetch(`${API_BASE_URL}/ai/chat-stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message: text }),
      signal: controller.signal,
    });

    if (!response.ok || !response.body) {
      throw new Error("Streaming request failed.");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");

    let buffer = ""; // store EVERYTHING streamed

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      const chunk = decoder.decode(value, { stream: true });
      if (!chunk) continue;

      buffer += chunk;

      // Detect final JSON block from backend
      if (buffer.includes("[[FINAL_JSON]]")) {
        const start = buffer.indexOf("[[FINAL_JSON]]") + 14;
        const end = buffer.indexOf("[[/FINAL_JSON]]");

        if (end !== -1) {
          const jsonStr = buffer.substring(start, end);
          try {
            const finalData = JSON.parse(jsonStr);
            onFinalJson(finalData);
          } catch (err) {
            console.error("JSON parse error:", err);
          }
        }
        continue; // skip streaming text during final JSON
      }

      // Normal streaming text update
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === botMessageId
            ? { ...msg, text: (msg.text ?? "") + chunk }
            : msg
        )
      );
    }

    streamAbortRef.current = null;
  };

  // ============================================================
  // 🔥 SEND MESSAGE (stream + parse final parlay)
  // ============================================================
  const sendMessage = async (e) => {
    e.preventDefault();
    if (!input.trim()) return;

    const messageText = input.trim();
    const userMsg = { id: makeId(), sender: "user", text: messageText };
    const botPlaceholder = { id: makeId(), sender: "bot", text: "" };

    setMessages((prev) => [...prev, userMsg, botPlaceholder]);
    setInput("");
    setLoading(true);

    try {
      // Stream + get final parlay JSON
      await streamReply(messageText, botPlaceholder.id, (final) => {
        console.log("🎯 FINAL STREAM JSON:", final);

        if (final.parsed_parlay) {
          // Replace placeholder with parlay UI
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === botPlaceholder.id
                ? { ...msg, parlay: final.parsed_parlay, text: "" }
                : msg
            )
          );
        }
      });
    } catch (err) {
      console.error("❌ Chat error:", err);

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === botPlaceholder.id
            ? {
                ...msg,
                text:
                  "⚠️ Unable to stream reply right now. Please try again shortly.",
              }
            : msg
        )
      );
    } finally {
      setLoading(false);
    }
  };

  // ============================================================
  // 🔥 RENDER UI
  // ============================================================
  return (
    <div className="flex flex-col items-center h-screen bg-gray-50 p-4">
      <h1 className="text-2xl font-semibold mb-4">🎯 AI Parlay Assistant</h1>

      <div className="max-w-2xl w-full bg-white shadow-md rounded-xl flex flex-col p-4 overflow-y-auto flex-grow mb-4 border">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`my-2 ${m.sender === "user" ? "text-right" : "text-left"}`}
          >
            {/* If parlay exists → show card */}
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

      {/* Input Box */}
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
