"use client";

import { useEffect, useRef, useState } from "react";
import {
  Camera,
  Target,
  Upload,
  ChevronDown,
  ChevronUp,
  Calculator,
  Crosshair,
  MapPin,
  Search,
  Send,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import {
  detectFromFile,
  detectFromSample,
  getSamples,
  logInspection,
  reverseGeocode,
  searchPlaces,
} from "@/lib/api";
import type { DetectionResult, GeocodeResult } from "@/lib/types";

const CONF_THRESHOLD = 0.25;

export function DetectorView() {
  const [samples, setSamples] = useState<string[]>([]);
  const [selectedSample, setSelectedSample] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<DetectionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isMethodologyOpen, setIsMethodologyOpen] = useState(true);
  const [lastFilename, setLastFilename] = useState("uploaded.jpg");
  const [roadName, setRoadName] = useState("");
  const [coords, setCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [place, setPlace] = useState<GeocodeResult | null>(null);
  const [isLocating, setIsLocating] = useState(false);
  const [isLogging, setIsLogging] = useState(false);
  const [logStatus, setLogStatus] = useState<string | null>(null);
  const [placeQuery, setPlaceQuery] = useState("");
  const [placeResults, setPlaceResults] = useState<GeocodeResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const loadSamples = () => {
      getSamples()
        .then((res) => setSamples(res.samples))
        .catch(() => setSamples([]));
    };

    loadSamples();

    const onRefresh = () => {
      loadSamples();
    };

    window.addEventListener("crackmap:refresh", onRefresh);
    return () => window.removeEventListener("crackmap:refresh", onRefresh);
  }, []);

  async function runDetection(promise: Promise<DetectionResult>) {
    setIsAnalyzing(true);
    setError(null);
    try {
      const data = await promise;
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Detection failed");
    } finally {
      setIsAnalyzing(false);
    }
  }

  function handleSampleChange(name: string) {
    setSelectedSample(name);
    if (!name) return;
    setLogStatus(null);
    setLastFilename(name);
    void runDetection(detectFromSample(name, CONF_THRESHOLD));
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setLogStatus(null);
    setLastFilename(file.name);
    void runDetection(detectFromFile(file, CONF_THRESHOLD));
    e.target.value = "";
  }

  /** GPS fix -> real OpenStreetMap street name, so the case carries a real address. */
  function useMyLocation() {
    if (!navigator.geolocation) {
      setLogStatus("Geolocation is not supported in this browser.");
      return;
    }
    setIsLocating(true);
    setLogStatus(null);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const next = { lat: pos.coords.latitude, lon: pos.coords.longitude };
        setCoords(next);
        try {
          const resolved = await reverseGeocode(next.lat, next.lon);
          setPlace(resolved);
          // Never clobber a name the inspector typed themselves.
          setRoadName((current) => current.trim() || resolved.road_name);
        } catch {
          setLogStatus(
            "Captured the coordinates, but the address lookup failed — type the road name manually."
          );
        } finally {
          setIsLocating(false);
        }
      },
      () => {
        setLogStatus("Could not get your location. You can still log with just a road name.");
        setIsLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  /** For logging a road you are not standing on — desk triage of a photo. */
  async function handlePlaceSearch(e: React.FormEvent) {
    e.preventDefault();
    if (placeQuery.trim().length < 2) return;
    setIsSearching(true);
    setLogStatus(null);
    try {
      setPlaceResults(await searchPlaces(placeQuery.trim()));
    } catch (err) {
      setLogStatus(err instanceof Error ? err.message : "Place search failed");
    } finally {
      setIsSearching(false);
    }
  }

  function choosePlace(result: GeocodeResult) {
    if (result.lat === null || result.lon === null) return;
    setCoords({ lat: result.lat, lon: result.lon });
    setPlace(result);
    setRoadName(result.road_name);
    setPlaceResults([]);
    setPlaceQuery("");
  }

  async function handleLogToCivicReport() {
    if (!result || !roadName.trim()) return;
    setIsLogging(true);
    setLogStatus(null);
    try {
      await logInspection({
        filename: lastFilename,
        road_name: roadName.trim(),
        lat: coords?.lat ?? null,
        lon: coords?.lon ?? null,
        total_defects: result.total_defects,
        severity_score: result.severity_score,
        composite_damage_score: result.composite_damage_score,
        boxes: result.boxes,
        annotated_image: result.annotated_image,
        address: place?.display_name ?? null,
        ward: place?.ward ?? null,
        city: place?.city ?? null,
        state: place?.state ?? null,
        osm_road_type: place?.osm_road_type ?? null,
      });
      setLogStatus("success");
    } catch (err) {
      setLogStatus(err instanceof Error ? err.message : "Failed to log finding");
    } finally {
      setIsLogging(false);
    }
  }

  const defectLabel = result
    ? `${result.total_defects} ${result.total_defects === 1 ? "defect" : "defects"}`
    : "";

  return (
    <div>
      <div className="workspace-header">
        <div>
          <h3 className="section-headline">
            <Camera size={22} />
            AI Road Damage Inspection Studio
          </h3>
          <p className="section-subtext" style={{ marginBottom: 0 }}>
            Upload road photos (aerial, drone, dashcam, or smartphone). The YOLOv8 detector localizes asphalt surface potholes.
          </p>
        </div>
        <div className="workspace-header-actions">
          <span className="workspace-header-label">Benchmark Presets:</span>
          <select
            className="sample-select"
            value={selectedSample}
            onChange={(e) => handleSampleChange(e.target.value)}
          >
            <option value="">-- Choose Sample --</option>
            {samples.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="upload-dropzone" onClick={() => fileInputRef.current?.click()}>
        <div className="dropzone-icon">
          <Upload size={32} />
        </div>
        <div className="dropzone-text">Click to Upload Road Image to Inspect</div>
        <div className="dropzone-hint">
          Supports JPG, PNG, WEBP · YOLOv8 single-class pothole detector
        </div>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          style={{ display: "none" }}
          onChange={handleFileChange}
        />
      </div>

      {error && (
        <p className="batch-status error" style={{ marginBottom: 20 }}>
          {error}
        </p>
      )}

      {(isAnalyzing || result) && (
        <div className="results-grid">
          <div className="image-card">
            <h4>Original Roadway Frame</h4>
            {result && (
              // eslint-disable-next-line @next/next/no-img-element -- base64 data URI, next/image adds no value here
              <img className="preview-img" src={result.original_image} alt="Original road frame" />
            )}
          </div>
          <div className="image-card">
            <div className="image-card-header">
              <h4>
                <Target size={16} />
                Detected Road Defects (YOLOv8)
              </h4>
              <span className="latency-badge">
                {isAnalyzing
                  ? "Analyzing..."
                  : result
                    ? `${result.inference_time_ms} ms · ${defectLabel} · Damage Score: ${result.composite_damage_score}/100`
                    : "-- ms"}
              </span>
            </div>
            {result && (
              // eslint-disable-next-line @next/next/no-img-element -- base64 data URI, next/image adds no value here
              <img className="preview-img" src={result.annotated_image} alt="Annotated road frame" />
            )}
          </div>
        </div>
      )}

      {result && result.boxes.length > 0 && (
        <div>
          <h4 style={{ fontSize: "1.1rem", fontWeight: 800, marginBottom: 8 }}>Detected Defect Inventory</h4>
          <div className="table-container">
            <table className="defect-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Code</th>
                  <th>Damage Name</th>
                  <th>Category</th>
                  <th>Severity</th>
                  <th>Confidence</th>
                  <th>Bounding Box [X1, Y1, X2, Y2]</th>
                  <th>Area (px²)</th>
                </tr>
              </thead>
              <tbody>
                {result.boxes.map((b) => (
                  <tr key={b.index}>
                    <td>
                      <strong>{b.index}</strong>
                    </td>
                    <td>
                      <span
                        className="defect-pill"
                        style={{ background: `${b.color}26`, color: b.color, border: `1px solid ${b.color}` }}
                      >
                        {b.code}
                      </span>
                    </td>
                    <td>
                      <strong>{b.name}</strong>
                    </td>
                    <td>{b.category}</td>
                    <td>
                      <span
                        style={{
                          color: b.severity === "Severe" || b.severity === "Critical" ? "#ef4444" : b.severity === "Moderate" ? "#f59e0b" : "#16a34a",
                          fontWeight: 700,
                        }}
                      >
                        {b.severity}
                      </span>
                    </td>
                    <td>{b.confidence}%</td>
                    <td>
                      <code>[{b.box.join(", ")}]</code>
                    </td>
                    <td>{b.area.toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {result && result.total_defects > 0 && (
        <section className="log-finding-card">
          <header>
            <MapPin size={18} />
            <div>
              <strong>Log this finding to the civic pipeline</strong>
              <span>
                A location turns a detection into a municipal grievance — it decides which authority owns
                the road, how the defect is triaged and what the repair is estimated to cost.
              </span>
            </div>
          </header>

          <div className="log-finding-grid">
            <label className="log-field">
              <span>Road / location name</span>
              <input
                type="text"
                placeholder="e.g. Hill Road, Bandra West"
                value={roadName}
                onChange={(e) => setRoadName(e.target.value)}
              />
            </label>

            <div className="log-field">
              <span>Coordinates</span>
              <button
                type="button"
                className={`locate-btn${coords ? " has-fix" : ""}`}
                onClick={useMyLocation}
                disabled={isLocating}
              >
                {isLocating ? (
                  <Loader2 size={14} className="spin-animation" />
                ) : (
                  <Crosshair size={14} />
                )}
                {coords ? `${coords.lat.toFixed(5)}, ${coords.lon.toFixed(5)}` : "Use my GPS location"}
              </button>
            </div>

            <form className="log-field" onSubmit={handlePlaceSearch}>
              <span>Or look up a road</span>
              <div className="place-search">
                <input
                  type="text"
                  placeholder="Search OpenStreetMap…"
                  value={placeQuery}
                  onChange={(e) => setPlaceQuery(e.target.value)}
                />
                <button type="submit" disabled={isSearching || placeQuery.trim().length < 2}>
                  {isSearching ? <Loader2 size={14} className="spin-animation" /> : <Search size={14} />}
                </button>
              </div>
            </form>
          </div>

          {placeResults.length > 0 && (
            <ul className="place-results">
              {placeResults.map((candidate) => (
                <li key={`${candidate.lat}-${candidate.lon}-${candidate.display_name}`}>
                  <button type="button" onClick={() => choosePlace(candidate)}>
                    <strong>{candidate.road_name}</strong>
                    <span>{candidate.display_name}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          {place && (
            <div className="resolved-place">
              <CheckCircle2 size={14} />
              <div>
                <strong>Resolved to {place.road_name}</strong>
                <span>
                  {place.display_name}
                  {place.osm_road_type ? ` · OSM highway=${place.osm_road_type}` : ""}
                </span>
              </div>
            </div>
          )}

          <div className="log-finding-actions">
            <button
              type="button"
              className="primary-pill-btn"
              onClick={handleLogToCivicReport}
              disabled={!roadName.trim() || isLogging}
            >
              {isLogging ? <Loader2 size={15} className="spin-animation" /> : <Send size={15} />}
              Log finding for triage
            </button>
            <span className="civic-subtle-inline">
              {result.total_defects} pothole{result.total_defects === 1 ? "" : "s"} · severity{" "}
              {result.severity_score}/5 · damage score {result.composite_damage_score}/100
            </span>
          </div>

          {logStatus === "success" && (
            <p className="log-success">
              <CheckCircle2 size={14} /> Logged and triaged. Open the <strong>Civic Pipeline</strong> tab —
              it is waiting in the intake queue.
            </p>
          )}
          {logStatus && logStatus !== "success" && <p className="batch-status error">{logStatus}</p>}
        </section>
      )}

      {/* Transparent Scoring & Severity Methodology Panel */}
      <div className="methodology-card" style={{ marginTop: 24, padding: "16px 20px", background: "#f8fafc", border: "1px solid #e2e8f0", borderRadius: 12 }}>
        <button
          type="button"
          onClick={() => setIsMethodologyOpen(!isMethodologyOpen)}
          style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%", background: "none", border: "none", cursor: "pointer", padding: 0, textAlign: "left" }}
          aria-expanded={isMethodologyOpen}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontWeight: 700, color: "#1e293b", fontSize: "0.95rem" }}>
            <Calculator size={18} style={{ color: "#3b82f6" }} />
            <span>How Damage Scores and Severity Bands Are Calculated</span>
          </div>
          {isMethodologyOpen ? <ChevronUp size={18} style={{ color: "#64748b" }} /> : <ChevronDown size={18} style={{ color: "#64748b" }} />}
        </button>

        {isMethodologyOpen && (
          <div style={{ marginTop: 14, fontSize: "0.875rem", color: "#334155", lineHeight: 1.6 }}>
            <div style={{ marginBottom: 12 }}>
              <strong style={{ color: "#0f172a" }}>1. Severity Band Thresholds (Frame Coverage):</strong>
              <ul style={{ margin: "6px 0 6px 20px", padding: 0 }}>
                <li><strong style={{ color: "#16a34a" }}>Low:</strong> Bounding box covers under 1.0% of the image frame (score weight = 1.5).</li>
                <li><strong style={{ color: "#f59e0b" }}>Moderate:</strong> Bounding box covers 1.0% to 4.0% of the image frame (score weight = 3.0).</li>
                <li><strong style={{ color: "#ef4444" }}>Severe:</strong> Bounding box covers over 4.0% of the image frame (score weight = 5.0).</li>
              </ul>
              <p style={{ margin: "4px 0 0", color: "#64748b", fontSize: "0.82rem" }}>
                <em>Note: Frame coverage is a 2D image proxy for apparent defect size in the photograph. It is not a measurement of real-world depth or physical metric dimensions, which vary with camera distance, sensor resolution, and viewing angle.</em>
              </p>
            </div>

            <div>
              <strong style={{ color: "#0f172a" }}>2. Composite Damage Score Formula:</strong>
              <div style={{ margin: "6px 0", padding: "8px 12px", background: "#f1f5f9", borderRadius: 6, fontFamily: "monospace", fontSize: "0.85rem", color: "#0f172a" }}>
                composite_damage_score = max(15, 100 − (total_defects × 12) − (average_severity_score × 3.5))
              </div>
              <p style={{ margin: "4px 0 0", color: "#64748b", fontSize: "0.82rem" }}>
                <em>Disclaimer: This formula is a custom heuristic designed specifically for this pothole detection pipeline, where 100 represents an anomaly-free frame. It is not the ASTM D6433 Pavement Condition Index standard.</em>
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
