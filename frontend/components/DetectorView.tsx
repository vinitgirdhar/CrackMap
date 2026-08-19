"use client";

import { useEffect, useRef, useState } from "react";
import { Camera, Target, Upload } from "lucide-react";
import { detectFromFile, detectFromSample, getSamples } from "@/lib/api";
import type { DetectionResult } from "@/lib/types";

const CONF_THRESHOLD = 0.25;

export function DetectorView() {
  const [samples, setSamples] = useState<string[]>([]);
  const [selectedSample, setSelectedSample] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<DetectionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getSamples()
      .then((res) => setSamples(res.samples))
      .catch(() => setSamples([]));
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

  return (
    <div>
      <div className="workspace-header">
        <div>
          <h3 className="section-headline">
            <Camera size={22} />
            AI Road Damage Inspection Studio
          </h3>
          <p className="section-subtext" style={{ marginBottom: 0 }}>
            Upload road photos (aerial, drone, dashcam, or smartphone). The AI isolates asphalt and flags
            potholes and cracks.
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
          Supports JPG, PNG, WEBP · Automatic road surface masking (0% tree false positives)
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
                Detected Road Defects (Asphalt Corridor)
              </h4>
              <span className="latency-badge">
                {isAnalyzing
                  ? "Analyzing..."
                  : result
                    ? `${result.inference_time_ms} ms · ${result.total_defects} defects`
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
                          color: b.severity === "Critical" ? "#ef4444" : "#f59e0b",
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
    </div>
  );
}
