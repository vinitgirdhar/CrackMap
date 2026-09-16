"use client";

import { useRef, useState } from "react";
import { CheckCircle2, Loader2, ScanSearch, XCircle } from "lucide-react";
import type { CaseView } from "@/lib/types";

interface VerifyPanelProps {
  caseView: CaseView;
  onVerify: (file: File) => Promise<void>;
}

/**
 * Post-repair re-inspection.
 *
 * The after-photo goes through the same YOLOv8 detector that raised the
 * original finding, and the comparison decides the outcome — a repair that
 * still shows defects is sent back as rework rather than rubber-stamped.
 */
export function VerifyPanel({ caseView, onVerify }: VerifyPanelProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const verification = caseView.verification;
  const canVerify = caseView.status === "REPAIRED";

  async function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    e.target.value = "";
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      await onVerify(file);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Re-inspection failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="verify-panel">
      {verification && (
        <div className={`verify-result${verification.passed ? " passed" : " failed"}`}>
          <div className="verify-result-head">
            {verification.passed ? <CheckCircle2 size={18} /> : <XCircle size={18} />}
            <strong>
              {verification.passed
                ? "Re-inspection passed"
                : `Re-inspection failed — returned as rework (attempt ${verification.attempts})`}
            </strong>
          </div>
          <div className="verify-metrics">
            <div>
              <span>Defects before</span>
              <strong>{verification.defects_before}</strong>
            </div>
            <div>
              <span>Defects after</span>
              <strong>{verification.defects_after}</strong>
            </div>
            <div>
              <span>Cleared</span>
              <strong>{verification.effectiveness_pct.toFixed(0)}%</strong>
            </div>
            <div>
              <span>Damage score after</span>
              <strong>{verification.damage_score_after}/100</strong>
            </div>
          </div>
          {verification.annotated_image && (
            // eslint-disable-next-line @next/next/no-img-element -- base64 data URI, next/image adds no value here
            <img
              className="verify-image"
              src={verification.annotated_image}
              alt="Re-inspection detection frame"
            />
          )}
          <p className="civic-footnote">
            Pass rule: at most 34% of the originally detected defects may remain in the after-photo,
            scored by the same detector that found them. Source frame: {verification.filename}.
          </p>
        </div>
      )}

      {canVerify && (
        <>
          <button
            type="button"
            className="verify-dropzone"
            onClick={() => inputRef.current?.click()}
            disabled={busy}
          >
            {busy ? <Loader2 size={22} className="spin-animation" /> : <ScanSearch size={22} />}
            <span>
              <strong>{busy ? "Running detector on the after-photo…" : "Upload the after-photo"}</strong>
              <span>
                {verification
                  ? "Re-run the re-inspection once the rework is finished."
                  : "The detector re-scores the same road and decides pass or rework."}
              </span>
            </span>
          </button>
          <input
            ref={inputRef}
            type="file"
            accept="image/*"
            style={{ display: "none" }}
            onChange={handleFile}
          />
        </>
      )}

      {error && <p className="batch-status error">{error}</p>}
    </div>
  );
}
