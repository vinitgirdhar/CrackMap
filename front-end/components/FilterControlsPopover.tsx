"use client";

import { useEffect, useState, useRef } from "react";
import { X, RotateCcw, Check, Sliders } from "lucide-react";

interface FilterState {
  confidenceThreshold: number;
  iouThreshold: number;
  showLabels: boolean;
  highlightHazard: boolean;
  classes: {
    D00: boolean;
    D10: boolean;
    D20: boolean;
    D40: boolean;
    D43: boolean;
    D44: boolean;
  };
}

const DEFAULT_FILTERS: FilterState = {
  confidenceThreshold: 25,
  iouThreshold: 45,
  showLabels: true,
  highlightHazard: true,
  classes: {
    D00: true,
    D10: true,
    D20: true,
    D40: true,
    D43: true,
    D44: true,
  },
};

interface FilterControlsPopoverProps {
  isOpen: boolean;
  onClose: () => void;
}

export function FilterControlsPopover({ isOpen, onClose }: FilterControlsPopoverProps) {
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS);
  const [isSaved, setIsSaved] = useState(false);
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem("crackmap_filter_settings");
        if (saved) {
          // Persisted state must be read after mount, not in a lazy state
          // initialiser: localStorage does not exist during SSR and seeding
          // from it at render time would cause a hydration mismatch.
          // eslint-disable-next-line react-hooks/set-state-in-effect
          setFilters(JSON.parse(saved));
        }
      } catch {
        // use default
      }
    }
  }, []);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        onClose();
      }
    }
    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [isOpen, onClose]);

  const handleConfidenceChange = (val: number) => {
    setFilters((prev) => {
      const updated = { ...prev, confidenceThreshold: val };
      saveFilters(updated);
      return updated;
    });
  };

  const handleIouChange = (val: number) => {
    setFilters((prev) => {
      const updated = { ...prev, iouThreshold: val };
      saveFilters(updated);
      return updated;
    });
  };

  const handleToggleClass = (cls: keyof FilterState["classes"]) => {
    setFilters((prev) => {
      const updated = {
        ...prev,
        classes: { ...prev.classes, [cls]: !prev.classes[cls] },
      };
      saveFilters(updated);
      return updated;
    });
  };

  const handleToggleOption = (key: "showLabels" | "highlightHazard") => {
    setFilters((prev) => {
      const updated = { ...prev, [key]: !prev[key] };
      saveFilters(updated);
      return updated;
    });
  };

  const saveFilters = (newFilters: FilterState) => {
    if (typeof window !== "undefined") {
      localStorage.setItem("crackmap_filter_settings", JSON.stringify(newFilters));
      window.dispatchEvent(
        new CustomEvent("crackmap:filter-change", { detail: newFilters })
      );
      setIsSaved(true);
      setTimeout(() => setIsSaved(false), 1500);
    }
  };

  const handleReset = () => {
    setFilters(DEFAULT_FILTERS);
    saveFilters(DEFAULT_FILTERS);
  };

  if (!isOpen) return null;

  return (
    <div className="filter-popover-overlay" role="dialog" aria-modal="true" aria-label="Inspection & Filter Controls">
      <div className="filter-popover-card" ref={popoverRef}>
        <div className="popover-header">
          <div className="popover-title-group">
            <Sliders size={18} className="text-blue-500" style={{ color: "#3b82f6" }} />
            <h4>Inspection & Filter Controls</h4>
          </div>
          <div className="popover-actions">
            <button
              className="popover-icon-btn"
              onClick={handleReset}
              title="Reset to defaults"
              type="button"
            >
              <RotateCcw size={14} />
            </button>
            <button
              className="popover-icon-btn"
              onClick={onClose}
              title="Close"
              type="button"
            >
              <X size={16} />
            </button>
          </div>
        </div>

        <div className="popover-body">
          {/* Confidence Slider */}
          <div className="filter-group">
            <div className="filter-label-row">
              <label htmlFor="conf-slider">Confidence Threshold</label>
              <span className="filter-value-badge">{filters.confidenceThreshold}%</span>
            </div>
            <input
              id="conf-slider"
              type="range"
              min={5}
              max={95}
              step={5}
              value={filters.confidenceThreshold}
              onChange={(e) => handleConfidenceChange(Number(e.target.value))}
              className="styled-slider"
            />
            <span className="filter-hint">Minimum model detection confidence cutoff</span>
          </div>

          {/* NMS IoU Slider */}
          <div className="filter-group">
            <div className="filter-label-row">
              <label htmlFor="iou-slider">NMS IoU Threshold</label>
              <span className="filter-value-badge">{filters.iouThreshold}%</span>
            </div>
            <input
              id="iou-slider"
              type="range"
              min={10}
              max={90}
              step={5}
              value={filters.iouThreshold}
              onChange={(e) => handleIouChange(Number(e.target.value))}
              className="styled-slider"
            />
            <span className="filter-hint">Bounding box non-maximum suppression overlap</span>
          </div>

          {/* Damage Type Filter Chips */}
          <div className="filter-group">
            <label className="group-heading">Active Damage Classes</label>
            <div className="damage-chips-grid">
              {[
                { key: "D40" as const, name: "D40 Pothole / Rut", color: "#ef4444" },
                { key: "D20" as const, name: "D20 Alligator Crack", color: "#f97316" },
                { key: "D00" as const, name: "D00 Longitudinal", color: "#eab308" },
                { key: "D10" as const, name: "D10 Transverse", color: "#3b82f6" },
                { key: "D43" as const, name: "D43 Crosswalk Blur", color: "#8b5cf6" },
                { key: "D44" as const, name: "D44 Lane Blur", color: "#06b6d4" },
              ].map((item) => (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => handleToggleClass(item.key)}
                  className={`damage-chip-btn${filters.classes[item.key] ? " selected" : ""}`}
                >
                  <span
                    className="chip-dot"
                    style={{ backgroundColor: item.color }}
                  />
                  <span>{item.name}</span>
                  {filters.classes[item.key] && <Check size={12} className="ml-auto" />}
                </button>
              ))}
            </div>
          </div>

          {/* Display Overlays */}
          <div className="filter-group">
            <label className="group-heading">Visual Display Overlays</label>
            <div className="toggle-row">
              <span className="toggle-label">Render Class Labels on Frame</span>
              <label className="switch">
                <input
                  type="checkbox"
                  checked={filters.showLabels}
                  onChange={() => handleToggleOption("showLabels")}
                />
                <span className="slider round" />
              </label>
            </div>
            <div className="toggle-row">
              <span className="toggle-label">Highlight High-Severity Hazards (Red Glow)</span>
              <label className="switch">
                <input
                  type="checkbox"
                  checked={filters.highlightHazard}
                  onChange={() => handleToggleOption("highlightHazard")}
                />
                <span className="slider round" />
              </label>
            </div>
          </div>
        </div>

        <div className="popover-footer">
          <span className="status-saved-text">
            {isSaved ? "✓ Preferences applied in real-time" : "Auto-applied across inspection views"}
          </span>
          <button className="primary-popover-btn" onClick={onClose} type="button">
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
