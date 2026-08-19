"use client";

import { useState } from "react";
import { Settings2, SlidersHorizontal } from "lucide-react";
import type { TabKey } from "@/lib/types";
import { FilterControlsPopover } from "./FilterControlsPopover";
import { SettingsModal } from "./SettingsModal";

const SUB_TABS: { key: TabKey; label: string }[] = [
  { key: "detect", label: "Inspection Studio" },
  { key: "analytics", label: "Dataset Analytics" },
  { key: "train", label: "Model Fine-Tuning" },
];

interface SubNavRowProps {
  activeTab: TabKey;
  onTabChange: (tab: TabKey) => void;
}

export function SubNavRow({ activeTab, onTabChange }: SubNavRowProps) {
  const [isFilterOpen, setIsFilterOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  return (
    <>
      <div className="sub-nav-row">
        <div className="sub-filter-pills">
          {SUB_TABS.map((tab) => (
            <button
              key={tab.key}
              className={`sub-pill${activeTab === tab.key ? " active" : ""}`}
              onClick={() => onTabChange(tab.key)}
              type="button"
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="sub-tools-group">
          <button
            className={`action-circle-btn${isFilterOpen ? " is-active" : ""}`}
            title="Inspection & filter controls"
            onClick={() => setIsFilterOpen(!isFilterOpen)}
            type="button"
            aria-label="Inspection and filter controls"
          >
            <SlidersHorizontal size={16} />
          </button>
          <button
            className={`action-circle-btn${isSettingsOpen ? " is-active" : ""}`}
            title="System preferences & settings"
            onClick={() => setIsSettingsOpen(true)}
            type="button"
            aria-label="System settings"
          >
            <Settings2 size={16} />
          </button>
        </div>
      </div>

      <FilterControlsPopover
        isOpen={isFilterOpen}
        onClose={() => setIsFilterOpen(false)}
      />

      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
    </>
  );
}
