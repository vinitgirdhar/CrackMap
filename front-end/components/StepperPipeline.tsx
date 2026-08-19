import { Check } from "lucide-react";

interface StepperPipelineProps {
  hasSurveyData: boolean;
  gisDataLoaded: boolean;
}

interface StepNode {
  label: string;
  state: "done" | "active" | "pending";
}

/**
 * Each node reflects a real backend capability, not decoration:
 * road-corridor masking and AI defect localization run on every
 * /api/detect call, so they're always "done" capabilities. Hotspot
 * search reflects whether GIS data has actually been loaded this
 * session. The original's "Municipal Dispatch" / "Contractor Repair"
 * nodes had no backing capability and were cut rather than faked.
 */
export function StepperPipeline({ hasSurveyData, gisDataLoaded }: StepperPipelineProps) {
  const nodes: StepNode[] = [
    { label: "Capture Road Footage", state: hasSurveyData ? "done" : "pending" },
    { label: "Asphalt Corridor Masking", state: "done" },
    { label: "AI Defect Localization", state: "done" },
    { label: "Real-time Hotspot Search", state: gisDataLoaded ? "done" : "active" },
  ];

  const doneCount = nodes.filter((n) => n.state === "done").length;

  // Nodes are flex:1, so node i's center sits at (i + 0.5) / n of the row.
  // The track therefore starts at the first center and ends at the last one;
  // the fill covers whole segments between completed nodes and is clamped so
  // it can never run past the track (which used to overflow the page).
  const nodeCount = nodes.length;
  const edgePct = 50 / nodeCount;
  const trackWidthPct = 100 - 100 / nodeCount;
  const filledSegments = Math.max(0, doneCount - 1);
  const fillPct = nodeCount > 1 ? (filledSegments / (nodeCount - 1)) * trackWidthPct : 0;

  return (
    <div className="stepper-pipeline">
      <div className="stepper-track" style={{ left: `${edgePct}%`, width: `${trackWidthPct}%` }} />
      <div className="stepper-track-fill" style={{ left: `${edgePct}%`, width: `${fillPct}%` }} />
      {nodes.map((node, i) => (
        <div className="stepper-node" key={node.label}>
          <div className={`node-circle${node.state === "done" ? " done" : ""}${node.state === "active" ? " active" : ""}`}>
            {node.state === "done" ? <Check size={14} /> : i + 1}
          </div>
          <div className="node-label">{node.label}</div>
        </div>
      ))}
    </div>
  );
}
