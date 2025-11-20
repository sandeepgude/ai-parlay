import { useState } from "react";
import {
  Star,
  StarOff,
  Share2,
  Clipboard,
  ClipboardCheck,
  ChevronUp,
  ChevronDown,
} from "lucide-react";

export default function ParlayCard({ data = {} }) {
  const {
    sport,
    parlay,
    total_odds,
    potential_payout,
    reasoning,
    saved_parlay_id,
  } = data;

  // Backend occasionally returns the legs as an object or missing entirely.
  // Normalize to an array so rendering never explodes.
  const legs = Array.isArray(parlay)
    ? parlay
    : parlay && typeof parlay === "object"
    ? Object.values(parlay).filter(Boolean)
    : [];

  const [favorite, setFavorite] = useState(false);
  const [copied, setCopied] = useState(false);
  const [showReason, setShowReason] = useState(false);
  const [stake, setStake] = useState("");
  const [calculatedPayout, setCalculatedPayout] = useState(null);

  // -------------------------------------------------------
  // TEAM LOGO MAP (expand anytime)
  // -------------------------------------------------------
  const logoMap = {
    "lakers": "https://a.espncdn.com/i/teamlogos/nba/500/lal.png",
    "celtics": "https://a.espncdn.com/i/teamlogos/nba/500/bos.png",
    "warriors": "https://a.espncdn.com/i/teamlogos/nba/500/gs.png",
    "knicks": "https://a.espncdn.com/i/teamlogos/nba/500/ny.png",
    "heat": "https://a.espncdn.com/i/teamlogos/nba/500/mia.png",

    "patriots": "https://a.espncdn.com/i/teamlogos/nfl/500/ne.png",
    "chiefs": "https://a.espncdn.com/i/teamlogos/nfl/500/kc.png",
    "bills": "https://a.espncdn.com/i/teamlogos/nfl/500/buf.png",

    "yankees": "https://a.espncdn.com/i/teamlogos/mlb/500/nyy.png",
    "dodgers": "https://a.espncdn.com/i/teamlogos/mlb/500/lad.png",

    "rangers": "https://a.espncdn.com/i/teamlogos/nhl/500/nyr.png",
  };

  const getLogo = (teamName) => {
    if (!teamName) return null;
    const key = teamName.toLowerCase();
    const match = Object.keys(logoMap).find((k) => key.includes(k));
    return match ? logoMap[match] : null;
  };

  const iconBySport = {
    nba: "🏀",
    nfl: "🏈",
    mlb: "⚾",
    nhl: "🏒",
    soccer: "⚽",
  }[(sport || "").toLowerCase()] || "🎯";

  // -------------------------------------------------------
  // COPY FUNCTION
  // -------------------------------------------------------
  const copySlip = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 1400);
  };

  // -------------------------------------------------------
  // SHARE FUNCTION
  // -------------------------------------------------------
  const shareSlip = () => {
    const txt = `🔥 AI Parlay Slip\nSport: ${sport}\nOdds: ${total_odds}\nPotential Payout: $${potential_payout}`;
    const shareUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(
      txt
    )}`;
    window.open(shareUrl, "_blank");
  };

  // -------------------------------------------------------
  // PAYOUT CALCULATOR
  // -------------------------------------------------------
  const calculateReward = () => {
    if (!stake || isNaN(stake)) {
      setCalculatedPayout(null);
      return;
    }
    const reward = Number(stake) * Number(total_odds);
    setCalculatedPayout(reward.toFixed(2));
  };

  return (
    <div className="border rounded-xl p-4 bg-white shadow-sm hover:shadow-md transition relative">

      {/* ⭐ Favorite Button */}
      <button
        onClick={() => setFavorite(!favorite)}
        className="absolute top-2 right-2 text-yellow-500"
      >
        {favorite ? <Star fill="#facc15" /> : <StarOff />}
      </button>

      {/* Header */}
      <div className="flex justify-between items-center mb-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{iconBySport}</span>
          <h2 className="text-lg font-bold">AI Parlay Suggestion</h2>
        </div>

        {saved_parlay_id && (
          <div className="text-xs bg-green-100 text-green-700 px-2 py-1 rounded-lg">
            Saved ✓ ID: {saved_parlay_id}
          </div>
        )}
      </div>

      {/* Legs */}
      <div className="space-y-3 mt-3">
        {legs.map((leg, i) => {
          const logo = getLogo(leg.team || leg.selection);
          return (
            <div
              key={i}
              className="p-3 bg-gray-50 border rounded-lg text-sm shadow-sm flex items-center gap-3"
            >
              {logo && (
                <img
                  src={logo}
                  alt={leg.team}
                  className="w-8 h-8 rounded-full border shadow"
                />
              )}

              <div className="flex-1">
                <div className="font-semibold text-gray-900">
                  • {leg.team || leg.selection}
                </div>

                {leg.market && (
                  <div className="text-gray-600 text-xs">
                    Market: <b>{leg.market}</b>
                  </div>
                )}

                {leg.odds && (
                  <div className="text-gray-600 text-xs">
                    Odds: <b>{leg.odds}</b>
                  </div>
                )}

                {leg.reason && (
                  <div className="text-gray-500 text-xs italic mt-1">
                    {leg.reason}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Odds + payout */}
      <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="text-sm">
          <strong>Total Odds:</strong>{" "}
          <span className="text-blue-700 font-semibold">{total_odds}</span>
        </div>
        <div className="text-sm">
          <strong>Potential Payout:</strong>{" "}
          <span className="text-green-700 font-semibold">
            ${potential_payout}
          </span>
        </div>
      </div>

      {/* Stake → Reward Calculator */}
      <div className="mt-4">
        <label className="text-sm text-gray-600 font-medium">
          Calculate Reward:
        </label>
        <div className="flex gap-2 mt-1">
          <input
            type="number"
            inputMode="decimal"
            step="any"
            min="0"
            placeholder="Enter stake ($)"
            className="border p-2 rounded-lg text-sm w-32 bg-white text-gray-900 placeholder-gray-500"
            value={stake}
            onChange={(e) => setStake(e.target.value)}
          />
          <button
            onClick={calculateReward}
            className="px-3 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700"
          >
            Calculate
          </button>
        </div>

        {calculatedPayout && (
          <div className="mt-1 text-sm text-green-700 font-semibold">
            Reward: ${calculatedPayout}
          </div>
        )}
     
      {/* Buttons: Share + Copy */}
    
      </div>

      {/* Reasoning */}
      {reasoning && (
        <div className="mt-4">
          <button
            onClick={() => setShowReason(!showReason)}
            className="flex items-center gap-1 text-sm text-gray-600 hover:text-gray-800"
          >
            {showReason ? (
              <>
                <ChevronUp className="w-4 h-4" /> Hide AI Analysis
              </>
            ) : (
              <>
                <ChevronDown className="w-4 h-4" /> Show AI Analysis
              </>
            )}
          </button>

          {showReason && (
            <div className="mt-2 p-3 bg-gray-50 border rounded-lg text-sm text-gray-700 whitespace-pre-wrap">
              {reasoning}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
