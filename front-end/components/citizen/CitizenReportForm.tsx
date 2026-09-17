"use client";

import { useEffect, useRef, useState } from "react";
import {
  AlertTriangle,
  Camera,
  CheckCircle2,
  Crosshair,
  Loader2,
  MapPin,
  Search,
  Send,
  Upload,
} from "lucide-react";
import {
  createCase,
  detectFromFile,
  detectFromSample,
  getSamples,
  logInspection,
  reverseGeocode,
  searchPlaces,
  submitCase,
} from "@/lib/api";
import type { DetectionResult, GeocodeResult } from "@/lib/types";

const CONF_THRESHOLD = 0.25;

interface CitizenReportFormProps {
  onReported: (caseId: number) => void;
}

/**
 * Upload a photo, confirm a location, submit — the same detect-then-locate
 * interaction as the internal Inspection Studio, wired to a citizen-safe
 * outcome: this ends in a case that is filed immediately, not left sitting
 * in an intake queue for an inspector to notice.
 */
export function CitizenReportForm({ onReported }: CitizenReportFormProps) {
  const [samples, setSamples] = useState<string[]>([]);
  const [selectedSample, setSelectedSample] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<DetectionResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [lastFilename, setLastFilename] = useState("uploaded.jpg");

  const [roadName, setRoadName] = useState("");
  const [coords, setCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [place, setPlace] = useState<GeocodeResult | null>(null);
  const [isLocating, setIsLocating] = useState(false);
  const [placeQuery, setPlaceQuery] = useState("");
  const [placeResults, setPlaceResults] = useState<GeocodeResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    getSamples()
      .then((res) => setSamples(res.samples))
      .catch(() => setSamples([]));
  }, []);

  async function runDetection(promise: Promise<DetectionResult>) {
    setIsAnalyzing(true);
    setError(null);
    setResult(null);
    try {
      setResult(await promise);
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "We could not analyze that photo — try a different one."
      );
    } finally {
      setIsAnalyzing(false);
    }
  }

  function handleSampleChange(name: string) {
    setSelectedSample(name);
    if (!name) return;
    setSubmitError(null);
    setLastFilename(name);
    void runDetection(detectFromSample(name, CONF_THRESHOLD));
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setSubmitError(null);
    setLastFilename(file.name);
    void runDetection(detectFromFile(file, CONF_THRESHOLD));
    e.target.value = "";
  }

  /** GPS fix -> real OpenStreetMap street name. */
  function useMyLocation() {
    if (!navigator.geolocation) {
      setSubmitError("Location is not supported in this browser — type the road name instead.");
      return;
    }
    setIsLocating(true);
    setSubmitError(null);
    navigator.geolocation.getCurrentPosition(
      async (pos) => {
        const next = { lat: pos.coords.latitude, lon: pos.coords.longitude };
        setCoords(next);
        try {
          const resolved = await reverseGeocode(next.lat, next.lon);
          setPlace(resolved);
          setRoadName((current) => current.trim() || resolved.road_name);
        } catch {
          setSubmitError("Got your location, but could not look up the address — type the road name.");
        } finally {
          setIsLocating(false);
        }
      },
      () => {
        setSubmitError("Could not get your location. You can still report with just a road name.");
        setIsLocating(false);
      },
      { enableHighAccuracy: true, timeout: 10000 }
    );
  }

  async function handlePlaceSearch(e: React.FormEvent) {
    e.preventDefault();
    if (placeQuery.trim().length < 2) return;
    setIsSearching(true);
    setSubmitError(null);
    try {
      setPlaceResults(await searchPlaces(placeQuery.trim()));
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Place search failed");
    } finally {
      setIsSearching(false);
    }
  }

  function choosePlace(candidate: GeocodeResult) {
    if (candidate.lat === null || candidate.lon === null) return;
    setCoords({ lat: candidate.lat, lon: candidate.lon });
    setPlace(candidate);
    setRoadName(candidate.road_name);
    setPlaceResults([]);
    setPlaceQuery("");
  }

  async function handleSubmitReport() {
    if (!result || !roadName.trim()) return;
    setIsSubmitting(true);
    setSubmitError(null);
    try {
      const finding = await logInspection({
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
      const civicCase = await createCase([finding.id]);
      // Filing is mechanical registration (route by coordinate, mint a
      // grievance number) — no engineer judgement involved, so it happens the
      // moment a citizen finishes reporting rather than waiting for someone
      // to notice it in an intake queue. Tendering and awarding a contractor
      // still need a municipal engineer and stay on the ops dashboard.
      const filed = await submitCase(civicCase.id);
      onReported(filed.id);
    } catch (err) {
      setSubmitError(err instanceof Error ? err.message : "Could not submit your report. Please try again.");
    } finally {
      setIsSubmitting(false);
    }
  }

  const defectLabel = result
    ? `${result.total_defects} pothole${result.total_defects === 1 ? "" : "s"}`
    : "";

  return (
    <div className="citizen-card">
      <div className="citizen-step-head">
        <span className="citizen-step-badge">Step 1 of 2</span>
        <h1>
          <Camera size={22} />
          Upload a photo
        </h1>
        <p>Take or choose a clear photo of the damaged road. We check it instantly.</p>
      </div>

      {samples.length > 0 && (
        <label className="citizen-sample-picker">
          <span>Don&rsquo;t have a photo handy? Try an example</span>
          <select value={selectedSample} onChange={(e) => handleSampleChange(e.target.value)}>
            <option value="">-- Choose an example --</option>
            {samples.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </label>
      )}

      <div className="upload-dropzone" onClick={() => fileInputRef.current?.click()}>
        <div className="dropzone-icon">
          <Upload size={30} />
        </div>
        <div className="dropzone-text">Click to upload a photo</div>
        <div className="dropzone-hint">JPG, PNG or WEBP</div>
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          style={{ display: "none" }}
          onChange={handleFileChange}
        />
      </div>

      {error && <p className="batch-status error">{error}</p>}

      {(isAnalyzing || result) && (
        <div className="results-grid">
          <div className="image-card">
            <h4>Your photo</h4>
            {result && (
              // eslint-disable-next-line @next/next/no-img-element -- base64 data URI, next/image adds no value here
              <img className="preview-img" src={result.original_image} alt="Uploaded road photo" />
            )}
          </div>
          <div className="image-card">
            <div className="image-card-header">
              <h4>What we detected</h4>
              <span className="latency-badge">
                {isAnalyzing ? "Checking…" : result ? defectLabel : "—"}
              </span>
            </div>
            {result && (
              // eslint-disable-next-line @next/next/no-img-element -- base64 data URI, next/image adds no value here
              <img className="preview-img" src={result.annotated_image} alt="Detected road damage" />
            )}
          </div>
        </div>
      )}

      {result && result.total_defects === 0 && (
        <p className="citizen-no-defects">
          <AlertTriangle size={16} />
          We couldn&rsquo;t detect any potholes in this photo. Try a clearer or closer shot of the damage.
        </p>
      )}

      {result && result.total_defects > 0 && (
        <section className="citizen-locate-section">
          <div className="citizen-step-head">
            <span className="citizen-step-badge">Step 2 of 2</span>
            <h2>
              <MapPin size={20} />
              Confirm the location
            </h2>
            <p>This decides which municipal authority your report goes to.</p>
          </div>

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
                {isLocating ? <Loader2 size={14} className="spin-animation" /> : <Crosshair size={14} />}
                {coords ? `${coords.lat.toFixed(5)}, ${coords.lon.toFixed(5)}` : "Use my location"}
              </button>
            </div>

            <form className="log-field" onSubmit={handlePlaceSearch}>
              <span>Or search for a road</span>
              <div className="place-search">
                <input
                  type="text"
                  placeholder="Search a place…"
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
                <span>{place.display_name}</span>
              </div>
            </div>
          )}

          <button
            type="button"
            className="citizen-submit-btn"
            onClick={handleSubmitReport}
            disabled={!roadName.trim() || isSubmitting}
          >
            {isSubmitting ? <Loader2 size={17} className="spin-animation" /> : <Send size={17} />}
            {isSubmitting ? "Submitting your report…" : "Submit report"}
          </button>

          {submitError && <p className="batch-status error">{submitError}</p>}
        </section>
      )}
    </div>
  );
}
