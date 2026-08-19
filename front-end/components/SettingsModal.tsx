"use client";

import { useEffect, useState, useRef } from "react";
import { X, Settings2, RefreshCw, Volume2, Eye } from "lucide-react";

interface SettingsState {
  autoRefreshInterval: number; // in seconds (0 = off)
  enableAudioAlerts: boolean;
  highContrastBoxes: boolean;
}

const DEFAULT_SETTINGS: SettingsState = {
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
  const [savedSuccess, setSavedSuccess] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem("crackmap_system_settings");
        if (saved) {
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
              <h3>Display & Telemetry Preferences</h3>
              <p>Configure telemetry auto-refresh, audio cues, and visual overlays</p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose} type="button" aria-label="Close modal">
            <X size={18} />
          </button>
        </div>

        <div className="modal-body">
          {/* Telemetry Polling */}
          <div className="settings-section">
            <div className="section-label-group">
              <RefreshCw size={16} className="section-icon" />
              <h4>Telemetry Auto-Refresh Interval</h4>
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
              <Eye size={16} className="section-icon" />
              <h4>Visual Overlays & Cues</h4>
            </div>
            <div className="toggle-row">
              <span className="toggle-label">High-Contrast Defect Bounding Boxes (Enhanced Visibility)</span>
              <label className="switch">
                <input
                  type="checkbox"
                  checked={settings.highContrastBoxes}
                  onChange={(e) => setSettings({ ...settings, highContrastBoxes: e.target.checked })}
                />
                <span className="slider round" />
              </label>
            </div>
            <div className="toggle-row">
              <span className="toggle-label">Audible Notification on Pothole Detection</span>
              <label className="switch">
                <input
                  type="checkbox"
                  checked={settings.enableAudioAlerts}
                  onChange={(e) => setSettings({ ...settings, enableAudioAlerts: e.target.checked })}
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
            {savedSuccess ? "✓ Preferences Saved" : "Save Preferences"}
          </button>
        </div>
      </div>
    </div>
  );
}
