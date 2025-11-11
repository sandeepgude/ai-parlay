import { useState, useRef, useEffect } from "react";

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

    const botMsg = { sender: "bot", text: "" };
    setMessages((prev) => [...prev, botMsg]);

    const url = `http://127.0.0.1:8000/api/v1/ai/chat-stream?message=${encodeURIComponent(
      userMsg.text
    )}`;

    console.log("🚀 Opening EventSource to:", url);
    const eventSource = new EventSource(url);

    eventSource.onopen = () => {
      console.log("✅ SSE connection opened successfully");
    };

    eventSource.onmessage = (event) => {
      console.log("📩 SSE message received:", event.data);

      const chunk = event.data;
      if (chunk === "[DONE]") {
        console.log("✅ Stream finished");
        setLoading(false);
        eventSource.close();
        return;
      }

      // Append chunk to the last (bot) message
      setMessages((prev) => {
        const updated = [...prev];
        updated[updated.length - 1].text += chunk;
        return updated;
      });
    };

    eventSource.onerror = (err) => {
      console.error("❌ SSE error or connection closed:", err);
      setLoading(false);
      eventSource.close();
    };

    // Safety timeout (if server never closes)
    setTimeout(() => {
      if (loading) {
        console.warn("⚠️ Stream timeout — closing connection manually");
        eventSource.close();
        setLoading(false);
      }
    }, 30000);
  };

  return (
    <div className="flex flex-col items-center h-screen bg-gray-50 p-4">
      <h1 className="text-2xl font-semibold mb-4">🤖 AI Parlay Assistant</h1>

      <div
        className="max-w-2xl w-full bg-white shadow-md rounded-xl flex flex-col p-4 overflow-y-auto flex-grow mb-4 border"
        style={{ scrollBehavior: "smooth" }}
      >
        {messages.map((m, i) => (
          <div
            key={i}
            className={`my-2 ${
              m.sender === "user" ? "text-right" : "text-left"
            }`}
          >
            <p
              className={`inline-block px-4 py-2 rounded-2xl ${
                m.sender === "user"
                  ? "bg-blue-500 text-white"
                  : "bg-gray-200 text-gray-800"
              }`}
            >
              {m.text}
            </p>
          </div>
        ))}
        {loading && (
          <p className="text-gray-400 text-sm italic text-left mt-2">
            AI is thinking...
          </p>
        )}
        <div ref={chatEndRef} />
      </div>

      <form onSubmit={sendMessage} className="flex w-full max-w-2xl">
        <input
          className="flex-grow bg-gray-100 text-gray-900 border border-gray-300 rounded-l-xl p-3 outline-none focus:ring-2 focus:ring-blue-400"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask AI about any sport or parlay..."
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
