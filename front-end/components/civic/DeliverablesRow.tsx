"use client";

import { Award, FileJson, FileSpreadsheet, FileText } from "lucide-react";
import { caseCsvUrl, caseJsonUrl, certificateUrl, dossierUrl } from "@/lib/api";
import type { CaseView } from "@/lib/types";

/**
 * What the pipeline actually produces. Every case yields a filed dossier and
 * machine-readable exports; a verified one also yields a completion
 * certificate.
 */
export function DeliverablesRow({ caseView }: { caseView: CaseView }) {
  const certified = caseView.status === "VERIFIED" || caseView.status === "CLOSED";

  return (
    <div className="deliverables-row">
      <a className="deliverable-card" href={dossierUrl(caseView.id)} target="_blank" rel="noreferrer">
        <span className="deliverable-icon pdf">
          <FileText size={18} />
        </span>
        <span className="deliverable-body">
          <strong>Case dossier</strong>
          <span>
            Filing record, photographic evidence, priced BOQ, re-inspection and audit trail — PDF
          </span>
        </span>
      </a>

      {certified ? (
        <a
          className="deliverable-card"
          href={certificateUrl(caseView.id)}
          target="_blank"
          rel="noreferrer"
        >
          <span className="deliverable-icon cert">
            <Award size={18} />
          </span>
          <span className="deliverable-body">
            <strong>Completion certificate</strong>
            <span>Signed-off repair certificate with before/after detection counts — PDF</span>
          </span>
        </a>
      ) : (
        <div className="deliverable-card is-locked" aria-disabled>
          <span className="deliverable-icon cert">
            <Award size={18} />
          </span>
          <span className="deliverable-body">
            <strong>Completion certificate</strong>
            <span>Issued once the AI re-inspection passes</span>
          </span>
        </div>
      )}

      <a className="deliverable-card" href={caseJsonUrl(caseView.id)} target="_blank" rel="noreferrer">
        <span className="deliverable-icon json">
          <FileJson size={18} />
        </span>
        <span className="deliverable-body">
          <strong>Open-data record</strong>
          <span>Full case object for municipal data exchange — JSON</span>
        </span>
      </a>

      <a className="deliverable-card" href={caseCsvUrl(caseView.id)} target="_blank" rel="noreferrer">
        <span className="deliverable-icon csv">
          <FileSpreadsheet size={18} />
        </span>
        <span className="deliverable-body">
          <strong>Defect inventory</strong>
          <span>One row per detected pothole with coordinates and boxes — CSV</span>
        </span>
      </a>
    </div>
  );
}
