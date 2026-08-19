"use client";

import { Settings2, SlidersHorizontal } from "lucide-react";
import type { TabKey } from "@/lib/types";

const SUB_TABS: { key: TabKey; label: string }[] = [
  { key: "detect", label: "Details & AI Studio" },
  { key: "gis", label: "Geotagged GIS" },
  { key: "analytics", label: "Taxonomy Breakdown" },
  { key: "train", label: "Custom Fine-Tuning" },
];

interface SubNavRowProps {
  activeTab: TabKey;
  onTabChange: (tab: TabKey) => void;
}

export function SubNavRow({ activeTab, onTabChange }: SubNavRowProps) {
  return (
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
        <button className="action-circle-btn" title="Sort & filter" type="button">
          <SlidersHorizontal size={16} />
        </button>
        <button className="action-circle-btn" title="Settings" type="button">
          <Settings2 size={16} />
        </button>
      </div>
    </div>
  );
}
