export default function ParlayCard({ data }) {
  if (!data) return null;

  return (
    <div className="bg-gray-800 text-gray-100 p-4 rounded-xl space-y-4">
      <h3 className="text-lg font-semibold text-blue-400 mb-2">
        🧠 AI Parlay Suggestion
      </h3>

      <div className="space-y-3">
        {data.parlay?.map((item, idx) => (
          <div
            key={idx}
            className="border border-gray-700 rounded-lg p-3 bg-gray-900"
          >
            <p className="font-medium text-white">🏀 {item.match}</p>
            <p className="text-green-400">
              ✅ Pick: <span className="font-semibold">{item.selection}</span>
            </p>
            <p className="text-sm text-gray-400">
              💰 Odds: {item.odds} | 🏦 {item.bookmaker} ({item.implied_probability}%)
            </p>
          </div>
        ))}
      </div>

      <div className="border-t border-gray-700 pt-3 mt-3 text-sm text-gray-300">
        <p>📊 <span className="font-semibold">Total Odds:</span> {data.total_odds}</p>
        <p>💵 <span className="font-semibold">Potential Payout:</span> ${data.potential_payout}</p>
        {data.reasoning && (
          <p className="mt-2 text-gray-400 leading-relaxed">
            💡 {data.reasoning}
          </p>
        )}
      </div>
    </div>
  );
}
