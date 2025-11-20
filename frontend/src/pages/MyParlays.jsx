import { useEffect, useState } from "react";
import axiosClient from "../api/axiosClient";

export default function MyParlays() {
  const [parlays, setParlays] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchParlays();
  }, []);

  const fetchParlays = async () => {
    try {
      const res = await axiosClient.get("/parlays/all");
      setParlays(res.data.data || []);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!confirm("Delete this parlay?")) return;

    try {
      await axiosClient.delete(`/parlays/${id}`);
      setParlays((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <h1 className="text-3xl font-bold mb-4">My Parlays</h1>

      {loading && <p className="text-gray-400">Loading parlays...</p>}

      {!loading && parlays.length === 0 && (
        <p className="text-gray-400">No saved parlays yet.</p>
      )}

      <div className="space-y-4">
        {parlays.map((p) => (
          <div key={p.id} className="rounded-xl border p-4 shadow-sm bg-white">

            <div className="flex justify-between">
              <div className="font-bold text-lg">Parlay #{p.id}</div>
              <div className="text-sm text-blue-600">{p.sport}</div>
            </div>

            <div className="mt-2 space-y-1">
              {p.legs.map((leg, i) => (
                <div key={i} className="text-sm text-gray-700">
                  • {leg.team ?? "Unknown"} — {leg.market ?? "N/A"} ({leg.odds})
                  {leg.reason && (
                    <div className="text-xs text-gray-500 ml-4">
                      {leg.reason}
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div className="mt-2 text-sm">
              <b>Total Odds:</b> {p.total_odds}  
              <br />
              <b>Payout:</b> ${p.potential_payout}
            </div>

            {p.ai_response && (
              <div className="mt-3 text-xs text-gray-500 border-t pt-2">
                AI Breakdown: {p.ai_response}
              </div>
            )}

            <div className="text-xs text-gray-400 mt-2">
              {new Date(p.created_at).toLocaleString()}
            </div>

            <button
              onClick={() => handleDelete(p.id)}
              className="text-red-600 text-sm mt-3 underline"
            >
              Delete
            </button>

          </div>
        ))}
      </div>
    </div>
  );
}
