"use client";

import { useEffect, useRef, useState } from "react";
import { Camera, Target, Upload, Info, ChevronDown, ChevronUp, Calculator } from "lucide-react";
import { detectFromFile, detectFromSample, getSamples } from "@/lib/api";
import type { DetectionResult } from "@/lib/types";

const CONF_THRESHOLD = 0.25;

export function DetectorView() {
  const [samples, setSamples] = useState<string[]>([]);
  const [selectedSample, setSelectedSample] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<DetectionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isMethodologyOpen, setIsMethodologyOpen] = useState(true);
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
    void runDetection(detectFromSample(name, CONF_THRESHOLD));
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    void runDetection(detectFromFile(file, CONF_THRESHOLD));
    e.target.value = "";
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
