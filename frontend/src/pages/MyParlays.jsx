import { useEffect, useState } from "react";
import axiosClient from "../api/axiosClient";
import { Card, CardHeader, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Loader2, Trash2, Eye } from "lucide-react";

export default function MyParlays() {
  const [parlays, setParlays] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const userId = 1; // TODO: Replace with logged-in user ID later

  // Fetch user's parlays
  useEffect(() => {
    async function fetchParlays() {
      try {
        const res = await axiosClient.get(`/parlays/${userId}`);
        setParlays(res.data.data);
      } catch (err) {
        console.error(err);
        setError("Failed to load parlays.");
      } finally {
        setLoading(false);
      }
    }
    fetchParlays();
  }, []);

  // Delete a parlay
  const handleDelete = async (id) => {
    if (!confirm("Are you sure you want to delete this parlay?")) return;
    try {
      await axiosClient.delete(`/parlays/${id}`);
      setParlays((prev) => prev.filter((p) => p.id !== id));
    } catch (err) {
      console.error(err);
      alert("Failed to delete parlay.");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="animate-spin w-8 h-8 text-gray-400" />
      </div>
    );
  }

  if (error) {
    return <p className="text-center text-red-400">{error}</p>;
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white px-6 py-10">
      <h1 className="text-3xl font-bold mb-6">📜 My Parlays</h1>

      {parlays.length === 0 ? (
        <p className="text-gray-400">No parlays yet. Go create one in Chat 💬</p>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {parlays.map((p) => (
            <Card
              key={p.id}
              className="bg-gray-900 border border-gray-800 hover:border-gray-700 transition"
            >
              <CardHeader>
                <h2 className="text-xl font-semibold">
                  {p.sport?.toUpperCase() || "Unknown Sport"}
                </h2>
                <p className="text-sm text-gray-400">
                  {new Date(p.created_at).toLocaleString()}
                </p>
              </CardHeader>

              <CardContent>
                <p className="text-gray-300 mb-2">
                  <span className="font-medium">Total Odds:</span>{" "}
                  {p.total_odds || "N/A"}
                </p>
                <p className="text-gray-400 text-sm mb-4 line-clamp-2">
                  {p.summary || "No summary available."}
                </p>

                <div className="flex justify-between">
                  <Button
                    size="sm"
                    variant="outline"
                    className="cursor-pointer hover:scale-105 transition-transform"
                  >
                    <Eye className="w-4 h-4 mr-1" /> View
                  </Button>
                  <Button
                    size="sm"
                    variant="destructive"
                    className="cursor-pointer hover:scale-105 transition-transform"
                    onClick={() => handleDelete(p.id)}
                  >
                    <Trash2 className="w-4 h-4 mr-1" /> Delete
                  </Button>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
