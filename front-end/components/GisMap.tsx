"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import {
  CircleMarker,
  LayersControl,
  MapContainer,
  Popup,
  TileLayer,
  Tooltip,
  useMap,
} from "react-leaflet";
import { getMapPoints } from "@/lib/api";
import { STAGE_META } from "@/lib/civic";
import type { CaseStatus, MapPoint } from "@/lib/types";

/** Only used until a first real finding arrives; every pin after that is real. */
const FALLBACK_CENTER: [number, number] = [20.5937, 78.9629];

interface GisMapProps {
  isActive: boolean;
  onDataLoaded?: (points: MapPoint[]) => void;
  focusPointId?: number | null;
  onSelectCase?: (caseId: number) => void;
}

/**
 * Keeps the viewport on the real data.
 *
 * Leaflet silently corrupts its pane size if it initialises inside a hidden
 * container, so `invalidateSize` runs whenever the tab becomes active. Bounds
 * are refitted as findings arrive, but only while the operator has not panned
 * away — yanking the map out from under someone mid-inspection is worse than a
 * slightly stale viewport.
 */
function ViewportController({
  isActive,
  points,
  focusPointId,
}: {
  isActive: boolean;
  points: MapPoint[];
  focusPointId?: number | null;
}) {
  const map = useMap();
  // Refs, not state: neither value is rendered, and refitting must not itself
  // trigger a render pass.
  const userMoved = useRef(false);
  const fittedCount = useRef(0);

  useEffect(() => {
    if (isActive) map.invalidateSize();
  }, [isActive, map]);

  useEffect(() => {
    const onDragEnd = () => {
      userMoved.current = true;
    };
    map.on("dragend", onDragEnd);
    return () => {
      map.off("dragend", onDragEnd);
    };
  }, [map]);

  useEffect(() => {
    if (points.length === 0 || points.length === fittedCount.current) return;
    if (userMoved.current && fittedCount.current > 0) return;
    const bounds = L.latLngBounds(points.map((p) => [p.lat, p.lon] as [number, number]));
    map.fitBounds(bounds, { padding: [48, 48], maxZoom: 16 });
    fittedCount.current = points.length;
  }, [points, map]);

  useEffect(() => {
    if (!focusPointId) return;
    const target = points.find((p) => p.id === focusPointId);
    if (target) map.flyTo([target.lat, target.lon], 17, { duration: 0.8 });
  }, [focusPointId, points, map]);

  return null;
}

function markerRadius(point: MapPoint): number {
  // Scale by severity, nudged up by how many potholes share the location.
  return 6 + point.severity_score * 2.2 + Math.min(6, point.total_defects);
}

export default function GisMap({ isActive, onDataLoaded, focusPointId, onSelectCase }: GisMapProps) {
  const [points, setPoints] = useState<MapPoint[]>([]);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await getMapPoints();
      setPoints(data);
      setError(null);
      onDataLoaded?.(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load map data");
    }
    // onDataLoaded is a render-stable callback in every caller; excluding it
    // keeps the poll from resubscribing on each parent render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    // The first poll is queued rather than run inline, so state only ever
    // changes from a callback the external system drives — never from the
    // effect body itself (React compiler lint), and a mount renders once.
    const first = setTimeout(load, 0);
    const id = setInterval(() => {
      if (typeof document !== "undefined" && document.hidden) return;
      void load();
    }, 4000);
    window.addEventListener("crackmap:refresh", load);
    return () => {
      clearTimeout(first);
      clearInterval(id);
      window.removeEventListener("crackmap:refresh", load);
    };
  }, [load]);

  return (
    <MapContainer
      center={FALLBACK_CENTER}
      zoom={5}
      minZoom={3}
      scrollWheelZoom
      style={{ height: "100%", width: "100%" }}
    >
      <ViewportController isActive={isActive} points={points} focusPointId={focusPointId} />

      <LayersControl position="topright">
        <LayersControl.BaseLayer checked name="Street">
          <TileLayer
            attribution="&copy; OpenStreetMap contributors"
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            subdomains={["a", "b", "c"]}
            maxZoom={19}
          />
        </LayersControl.BaseLayer>
        <LayersControl.BaseLayer name="Muted (labels on top)">
          <TileLayer
            attribution="&copy; OpenStreetMap contributors &copy; CARTO"
            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
            subdomains={["a", "b", "c", "d"]}
            maxZoom={19}
          />
        </LayersControl.BaseLayer>
        <LayersControl.BaseLayer name="Satellite">
          <TileLayer
            attribution="Tiles &copy; Esri — Source: Esri, Maxar, Earthstar Geographics"
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
            maxZoom={19}
          />
        </LayersControl.BaseLayer>
      </LayersControl>

      {points.map((point) => {
        const stageColor = point.case_id
          ? STAGE_META[point.case_status as CaseStatus]?.color ?? "#94a3b8"
          : "#94a3b8";
        return (
          <CircleMarker
            key={point.id}
            center={[point.lat, point.lon]}
            radius={markerRadius(point)}
            className={point.repaired ? "gis-marker repaired" : "gis-marker open"}
            pathOptions={{
              fillColor: point.repaired ? "#16a34a" : point.color_hex,
              // The ring carries the civic stage; the fill carries severity.
              color: stageColor,
              weight: 3,
              opacity: 1,
              fillOpacity: point.repaired ? 0.55 : 0.85,
            }}
          >
            <Tooltip direction="top" offset={[0, -6]} opacity={1}>
              <strong>{point.road_name}</strong> · {point.total_defects} pothole
              {point.total_defects === 1 ? "" : "s"}
            </Tooltip>
            <Popup>
              <div className="gis-popup">
                <strong>{point.road_name}</strong>
                <span className="gis-popup-address">{point.address}</span>
                <dl>
                  <div>
                    <dt>Severity</dt>
                    <dd style={{ color: point.color_hex }}>
                      {point.severity} ({point.severity_score}/5)
                    </dd>
                  </div>
                  <div>
                    <dt>Potholes</dt>
                    <dd>{point.total_defects}</dd>
                  </div>
                  <div>
                    <dt>Priority</dt>
                    <dd>{point.priority}</dd>
                  </div>
                  <div>
                    <dt>Road class</dt>
                    <dd>{point.road_class}</dd>
                  </div>
                  <div>
                    <dt>Damage score</dt>
                    <dd>{point.damage_score}/100</dd>
                  </div>
                  <div>
                    <dt>Mean confidence</dt>
                    <dd>{(point.confidence * 100).toFixed(0)}%</dd>
                  </div>
                  <div>
                    <dt>Coordinates</dt>
                    <dd>
                      {point.lat.toFixed(5)}, {point.lon.toFixed(5)}
                    </dd>
                  </div>
                </dl>
                {point.case_id ? (
                  <>
                    <div className="gis-popup-case" style={{ borderColor: stageColor, color: stageColor }}>
                      {STAGE_META[point.case_status as CaseStatus]?.label ?? point.case_status}
                      {point.tracking_id ? ` · ${point.tracking_id}` : ""}
                    </div>
                    {onSelectCase && (
                      <button type="button" onClick={() => onSelectCase(point.case_id!)}>
                        Open case #{point.case_id}
                      </button>
                    )}
                  </>
                ) : (
                  <div className="gis-popup-case unfiled">Not yet filed with any authority</div>
                )}
              </div>
            </Popup>
          </CircleMarker>
        );
      })}

      {error && <div className="gis-map-error">{error}</div>}
    </MapContainer>
  );
}
