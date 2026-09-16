"use client";

import { useCallback, useState } from "react";
import dynamic from "next/dynamic";
import { MapPinned, Satellite } from "lucide-react";
import { STAGE_META, STAGE_ORDER, formatAgo } from "@/lib/civic";
import { useNow } from "@/lib/hooks/useNow";
import type { MapPoint } from "@/lib/types";

const GisMap = dynamic(() => import("./GisMap"), { ssr: false });

interface GisViewProps {
  isActive: boolean;
  focusPointId?: number | null;
  onSelectCase?: (caseId: number) => void;
}

const SEVERITY_LEGEND = [
  { label: "Low", color: "#22c55e" },
  { label: "Moderate", color: "#f59e0b" },
  { label: "Severe", color: "#ef4444" },
  { label: "Repaired", color: "#16a34a" },
];

export function GisView({ isActive, focusPointId, onSelectCase }: GisViewProps) {
  const [points, setPoints] = useState<MapPoint[]>([]);
  const [loadedAt, setLoadedAt] = useState<number | null>(null);
  const now = useNow(1000, isActive);

  const handleDataLoaded = useCallback((next: MapPoint[]) => {
    setPoints(next);
    setLoadedAt(Date.now() / 1000);
  }, []);

  const repaired = points.filter((p) => p.repaired).length;
  const filed = points.filter((p) => p.case_id !== null).length;
  const stagesPresent = STAGE_ORDER.filter((stage) => points.some((p) => p.case_status === stage));

  return (
    <section className="civic-panel map-panel">
      <header className="civic-panel-head">
        <div>
          <h4>
            <MapPinned size={17} />
            Live damage map
            <span className="civic-count-chip">{points.length}</span>
          </h4>
          <p>
            Real coordinates from the field, reverse-geocoded to OpenStreetMap street names. Fill colour
            is severity, the ring is the case&rsquo;s civic stage.
          </p>
        </div>
        <div className="map-live-badge">
          <span className="live-dot" aria-hidden />
          {loadedAt ? `updated ${formatAgo(loadedAt, now)}` : "connecting…"}
        </div>
      </header>

      <div className="gis-map-container">
        <GisMap
          isActive={isActive}
          onDataLoaded={handleDataLoaded}
          focusPointId={focusPointId}
          onSelectCase={onSelectCase}
        />
        {points.length === 0 && (
          <div className="gis-map-empty">
            <Satellite size={24} />
            <strong>No geotagged findings yet</strong>
            <span>
              Log a detection with its location in the Inspection Studio — there are no demo pins, so the
              map only ever shows real inspection output.
            </span>
          </div>
        )}
      </div>

      <div className="map-legend">
        <div className="map-legend-group">
          <span className="map-legend-title">Severity (fill)</span>
          {SEVERITY_LEGEND.map((item) => (
            <span className="map-legend-item" key={item.label}>
              <i style={{ background: item.color }} />
              {item.label}
            </span>
          ))}
        </div>
        {stagesPresent.length > 0 && (
          <div className="map-legend-group">
            <span className="map-legend-title">Civic stage (ring)</span>
            {stagesPresent.map((stage) => (
              <span className="map-legend-item" key={stage}>
                <i className="ring" style={{ borderColor: STAGE_META[stage].color }} />
                {STAGE_META[stage].short}
              </span>
            ))}
          </div>
        )}
        <div className="map-legend-stats">
          {filed} of {points.length} filed · {repaired} verified repaired
        </div>
      </div>
    </section>
  );
}
