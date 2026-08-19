"use client";

import { useEffect, useState, useRef } from "react";
import { X, Settings2, Activity, Check, RefreshCw, Volume2, Globe, Server } from "lucide-react";
import { getSystemInfo } from "@/lib/api";

interface SettingsState {
  apiUrl: string;
  mapTileLayer: "carto-light" | "carto-dark" | "osm";
  autoRefreshInterval: number; // in seconds (0 = off)
  enableAudioAlerts: boolean;
  highContrastBoxes: boolean;
}

const DEFAULT_SETTINGS: SettingsState = {
  apiUrl: "http://localhost:8000",
  mapTileLayer: "carto-light",
  autoRefreshInterval: 0,
  enableAudioAlerts: false,
  highContrastBoxes: true,
};

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function SettingsModal({ isOpen, onClose }: SettingsModalProps) {
  const [settings, setSettings] = useState<SettingsState>(DEFAULT_SETTINGS);
  const [pingStatus, setPingStatus] = useState<"idle" | "testing" | "success" | "error">("idle");
  const [pingLatency, setPingLatency] = useState<number | null>(null);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem("crackmap_system_settings");
        if (saved) {
          // Persisted state must be read after mount, not in a lazy state
          // initialiser: localStorage does not exist during SSR and seeding
          // from it at render time would cause a hydration mismatch.
          // eslint-disable-next-line react-hooks/set-state-in-effect
          setSettings(JSON.parse(saved));
        }
      } catch {
        // fallback
      }
    }
  }, []);

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    if (isOpen) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose]);

  const handleTestConnection = async () => {
    setPingStatus("testing");
    const start = performance.now();
    try {
      await getSystemInfo();
      const latency = Math.round(performance.now() - start);
      setPingLatency(latency);
      setPingStatus("success");
    } catch {
      setPingStatus("error");
      setPingLatency(null);
    }
  };

  const handleSave = () => {
    if (typeof window !== "undefined") {
      localStorage.setItem("crackmap_system_settings", JSON.stringify(settings));
      window.dispatchEvent(
        new CustomEvent("crackmap:settings-change", { detail: settings })
      );
      setSavedSuccess(true);
      setTimeout(() => {
        setSavedSuccess(false);
        onClose();
      }, 700);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-label="CrackMap System Settings">
      <div className="settings-modal-card" ref={modalRef} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-group">
            <div className="modal-icon-badge">
              <Settings2 size={20} />
            </div>
            <div>
              <h3>System Settings & Preferences</h3>
              <p>Configure API endpoints, telemetry polling, and inspection overlays</p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose} type="button" aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          {/* API Endpoint Section */}
          <div className="settings-section">
            <div className="section-label-group">
              <Server size={16} className="section-icon" />
              <h4>Backend REST API Endpoint</h4>
            </div>
            <div className="api-input-row">
              <input
                type="text"
                value={settings.apiUrl}
                onChange={(e) => setSettings({ ...settings, apiUrl: e.target.value })}
                className="styled-text-input"
                placeholder="http://localhost:5000"
              />
              <button
                type="button"
                className={`ping-test-btn${pingStatus === "testing" ? " is-testing" : ""}`}
                onClick={handleTestConnection}
                disabled={pingStatus === "testing"}
              >
                {pingStatus === "testing" ? (
                  <RefreshCw size={14} className="spin-animation" />
                ) : (
                  <Activity size={14} />
                )}
                <span>Test Ping</span>
              </button>
            </div>
            {pingStatus === "success" && (
              <div className="connection-status-msg success">
                <span className="status-indicator-dot online" />
                <span>Connected successfully — Latency: {pingLatency}ms</span>
              </div>
            )}
            {pingStatus === "error" && (
              <div className="connection-status-msg error">
                <span className="status-indicator-dot offline" />
                <span>Could not reach backend at {settings.apiUrl}</span>
              </div>
            )}
          </div>

            {/* Telemetry Polling */}
          <div className="settings-section">
            <div className="section-label-group">
              <RefreshCw size={16} className="section-icon" />
              <h4>Telemetry Polling Interval</h4>
            </div>
            <div className="radio-pills-row">
              {[
                { val: 0, label: "Manual Only" },
                { val: 10, label: "Every 10s" },
                { val: 30, label: "Every 30s" },
                { val: 60, label: "Every 60s" },
              ].map((opt) => (
                <button
                  key={opt.val}
                  type="button"
                  onClick={() => setSettings({ ...settings, autoRefreshInterval: opt.val })}
                  className={`radio-pill-btn${settings.autoRefreshInterval === opt.val ? " active" : ""}`}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          </div>

          {/* Sound & Visuals */}
          <div className="settings-section">
            <div className="section-label-group">
              <Volume2 size={16} className="section-icon" />
              <h4>Alerts & High-Contrast Options</h4>
            </div>
            <div className="toggle-row">
              <span className="toggle-label">Audible Chime on Critical Pothole (`D40`) Detection</span>
              <label className="switch">
                <input
                  type="checkbox"
                  checked={settings.enableAudioAlerts}
                  onChange={(e) => setSettings({ ...settings, enableAudioAlerts: e.target.checked })}
                />
                <span className="slider round" />
              </label>
            </div>
            <div className="toggle-row">
              <span className="toggle-label">High-Contrast Thick Bounding Boxes for Low-Light</span>
              <label className="switch">
                <input
                  type="checkbox"
                  checked={settings.highContrastBoxes}
                  onChange={(e) => setSettings({ ...settings, highContrastBoxes: e.target.checked })}
                />
                <span className="slider round" />
              </label>
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button className="secondary-btn" onClick={onClose} type="button">
            Cancel
          </button>
          <button className="primary-modal-btn" onClick={handleSave} type="button">
            {savedSuccess ? "✓ Settings Saved" : "Save Preferences"}
          </button>
        </div>
      </div>
    </div>
  );
}
