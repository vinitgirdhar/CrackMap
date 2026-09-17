"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Route } from "lucide-react";
import { CitizenReportForm } from "./CitizenReportForm";
import { CitizenTracker } from "./CitizenTracker";

/**
 * Public, standalone citizen surface — separate from the internal ops
 * dashboard at "/". Two phases on one URL: report a pothole, then track it.
 *
 * The case id lives in the URL (`?case=<id>`) rather than only in React
 * state, so the tracking link is the same thing a citizen can bookmark,
 * close the tab on, and come back to later.
 */
export function CitizenReportPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const fromUrl = Number(searchParams.get("case"));
  const [caseId, setCaseId] = useState<number | null>(
    Number.isFinite(fromUrl) && fromUrl > 0 ? fromUrl : null
  );

  function handleReported(id: number) {
    setCaseId(id);
    router.replace(`/report?case=${id}`);
  }

  function handleReportAnother() {
    setCaseId(null);
    router.replace("/report");
  }

  return (
    <div className="citizen-page">
      <header className="citizen-header">
        <Link className="brand-logo" href="/">
          <Route size={22} strokeWidth={2.5} />
          Crack<span>Map</span>
        </Link>
        <span className="citizen-header-tag">Report a Pothole</span>
      </header>

      <main className="citizen-main">
        {caseId === null ? (
          <CitizenReportForm onReported={handleReported} />
        ) : (
          <CitizenTracker caseId={caseId} onReportAnother={handleReportAnother} />
        )}
      </main>

      <footer className="citizen-footer">
        Findings you report here go through the same municipal pipeline CrackMap runs for every road —
        filed with the authority that owns the road, triaged, repaired and AI-verified.
      </footer>
    </div>
  );
}
