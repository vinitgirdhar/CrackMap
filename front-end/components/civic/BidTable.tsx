"use client";

import { useState } from "react";
import { Gavel, Loader2, Star } from "lucide-react";
import { formatInr } from "@/lib/civic";
import type { Bid } from "@/lib/types";

interface BidTableProps {
  bids: Bid[];
  estimateInr: number | null;
  awardedContractorId?: number | null;
  onAward?: (contractorId: number) => Promise<void>;
}

/**
 * Tender board. Awarding is a real decision — lowest price is not always the
 * right pick once promised duration and contractor rating are on the table —
 * so this is a choice, not a Next button.
 */
export function BidTable({ bids, estimateInr, awardedContractorId, onAward }: BidTableProps) {
  const [busyId, setBusyId] = useState<number | null>(null);

  if (bids.length === 0) {
    return <p className="civic-subtle">No bids received yet.</p>;
  }

  const cheapest = Math.min(...bids.map((b) => b.quoted_inr));
  const fastest = Math.min(...bids.map((b) => b.promised_days));
  const bestRated = Math.max(...bids.map((b) => b.rating));

  async function handleAward(contractorId: number) {
    if (!onAward) return;
    setBusyId(contractorId);
    try {
      await onAward(contractorId);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="table-container">
      <table className="defect-table civic-table bid-table">
        <thead>
          <tr>
            <th>Contractor</th>
            <th>Quote</th>
            <th>vs estimate</th>
            <th>Duration</th>
            <th>Rating</th>
            {onAward && <th aria-label="award" />}
          </tr>
        </thead>
        <tbody>
          {bids.map((bid) => {
            const isAwarded = awardedContractorId === bid.contractor_id;
            return (
              <tr key={bid.contractor_id} className={isAwarded ? "is-awarded" : undefined}>
                <td>
                  <strong>{bid.contractor_name}</strong>
                  <span className="civic-subtle">
                    {bid.specialty} · {bid.service_area}
                  </span>
                </td>
                <td className="num">
                  <strong>{formatInr(bid.quoted_inr)}</strong>
                  {bid.quoted_inr === cheapest && <span className="bid-tag lowest">lowest</span>}
                </td>
                <td className="num" style={{ color: bid.variance_pct <= 0 ? "#16a34a" : "#ef4444" }}>
                  {bid.variance_pct > 0 ? "+" : ""}
                  {bid.variance_pct.toFixed(1)}%
                </td>
                <td className="num">
                  {bid.promised_days.toFixed(0)}d
                  {bid.promised_days === fastest && <span className="bid-tag fastest">fastest</span>}
                </td>
                <td className="num">
                  <span className="bid-rating">
                    <Star size={11} /> {bid.rating.toFixed(1)}
                  </span>
                  {bid.rating === bestRated && <span className="bid-tag rated">top rated</span>}
                </td>
                {onAward && (
                  <td>
                    {isAwarded ? (
                      <span className="bid-awarded-chip">Awarded</span>
                    ) : (
                      <button
                        type="button"
                        className="primary-pill-btn sm"
                        disabled={busyId !== null}
                        onClick={() => void handleAward(bid.contractor_id)}
                      >
                        {busyId === bid.contractor_id ? (
                          <Loader2 size={13} className="spin-animation" />
                        ) : (
                          <Gavel size={13} />
                        )}
                        Award
                      </button>
                    )}
                  </td>
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
      {estimateInr !== null && (
        <p className="civic-footnote">
          Engineer&rsquo;s estimate {formatInr(estimateInr)}. Quotes are generated per contractor from their
          own rate multiplier and crew capacity, and stay fixed for the life of the tender.
        </p>
      )}
    </div>
  );
}
