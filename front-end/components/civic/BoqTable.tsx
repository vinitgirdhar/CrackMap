"use client";

import { formatInr } from "@/lib/civic";
import type { Boq } from "@/lib/types";

/** Priced bill of quantities — the costed output attached to a work order. */
export function BoqTable({ boq }: { boq: Boq }) {
  return (
    <div className="boq-block">
      <div className="table-container">
        <table className="defect-table civic-table boq-table">
          <thead>
            <tr>
              <th>Item</th>
              <th>Qty</th>
              <th>Rate</th>
              <th>Amount</th>
            </tr>
          </thead>
          <tbody>
            {boq.lines.map((line) => (
              <tr key={line.description}>
                <td>{line.description}</td>
                <td className="num">
                  {line.quantity}
                  <span className="civic-subtle-inline"> {line.unit}</span>
                </td>
                <td className="num">{formatInr(line.rate_inr)}</td>
                <td className="num">
                  <strong>{formatInr(line.amount_inr)}</strong>
                </td>
              </tr>
            ))}
          </tbody>
          <tfoot>
            <tr>
              <td colSpan={3}>Subtotal</td>
              <td className="num">{formatInr(boq.subtotal_inr)}</td>
            </tr>
            <tr>
              <td colSpan={3}>Net payable before tax</td>
              <td className="num">{formatInr(boq.net_inr)}</td>
            </tr>
            <tr>
              <td colSpan={3}>GST @ 18%</td>
              <td className="num">{formatInr(boq.gst_inr)}</td>
            </tr>
            <tr className="boq-total">
              <td colSpan={3}>Engineer&rsquo;s estimate</td>
              <td className="num">{formatInr(boq.total_inr)}</td>
            </tr>
          </tfoot>
        </table>
      </div>
      <p className="civic-footnote">
        Patch footprints come from each defect&rsquo;s severity band (Low 0.18 m², Moderate 0.55 m², Severe
        1.20 m²) because frame coverage is a 2D photographic proxy, not a survey measurement. Unit rates
        sit in the band published in state Schedule-of-Rates books for bituminous pothole repair.
      </p>
    </div>
  );
}
