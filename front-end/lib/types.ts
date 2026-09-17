export interface DashboardSummary {
  dataset_name: string;
  total_images: number;
  damaged_images: number;
  undamaged_images: number;
  total_defects: number;
  potholes_count: number;
  cracks_count: number;
  other_count: number;
  avg_severity: number;
  composite_damage_score: number;
  class_distribution: Record<string, number>;
  is_demo_data?: boolean;
}

export interface SystemInfo {
  status: string;
  torch_version: string;
  cuda_available: boolean;
  device: string;
  models_loaded: string[];
  models_available?: string[];
  fine_tuned?: boolean;
}

export interface SamplesList {
  samples: string[];
}

export interface DetectionBox {
  index: number;
  code: string;
  name: string;
  category: string;
  severity: string;
  severity_score: number;
  color: string;
  confidence: number;
  box: [number, number, number, number];
  area: number;
}

export interface DetectionResult {
  success: boolean;
  inference_time_ms: number;
  total_defects: number;
  severity_score: number;
  composite_damage_score: number;
  boxes: DetectionBox[];
  annotated_image: string;
  original_image: string;
  road_mask: string;
}

export interface UploadedItem {
  filename: string;
  defects_found: number;
  width: number;
  height: number;
}

export interface UploadPotholeImagesResult {
  success: boolean;
  message: string;
  dataset_path: string;
  items: UploadedItem[];
}

export type TrainingStatus = "idle" | "training" | "completed" | "failed";

export interface TrainingLossEntry {
  epoch: number;
  loss: number;
}

export interface TrainingJobStatus {
  status: TrainingStatus;
  progress: number;
  current_epoch: number;
  total_epochs: number;
  current_loss: number;
  losses: TrainingLossEntry[];
  checkpoint_path: string;
  error: string | null;
}

export interface StartTrainingResult {
  success: boolean;
  message: string;
  epochs?: number;
  architecture?: string;
}

export interface StartTrainingParams {
  epochs: number;
  batch_size: number;
  learning_rate: number;
  architecture: string;
}

export interface DatasetStats {
  dataset_name: string;
  ingestion_date: string;
  total_images: number;
  damaged_images: number;
  undamaged_images: number;
  total_boxes: number;
  train_images: number;
  val_images: number;
  test_images: number;
  precision?: number;
  recall?: number;
  map50?: number;
  map50_95?: number;
  architecture?: string;
  epochs_trained?: number;
  class_distribution: Record<string, number>;
  is_demo_data?: boolean;
}

export type TabKey = "detect" | "analytics" | "civic";

/* ── Civic pipeline ────────────────────────────────────────────────────── */

export type CaseStatus =
  | "DRAFT"
  | "SUBMITTED"
  | "ACKNOWLEDGED"
  | "TENDERED"
  | "WORK_ORDERED"
  | "IN_REPAIR"
  | "REPAIRED"
  | "VERIFIED"
  | "CLOSED";

export type SlaState = "NOT_STARTED" | "ON_TRACK" | "AT_RISK" | "BREACHED" | "MET";

export interface GeocodeResult {
  road_name: string;
  road: string;
  ward: string;
  city: string;
  state: string;
  postcode: string;
  country: string;
  display_name: string;
  osm_road_type: string;
  lat: number | null;
  lon: number | null;
}

export interface Inspection {
  id: number;
  filename: string;
  road_name: string;
  lat: number | null;
  lon: number | null;
  address: string | null;
  ward: string | null;
  city: string | null;
  state: string | null;
  osm_road_type: string | null;
  road_class: string | null;
  total_defects: number;
  severity_score: number;
  composite_damage_score: number;
  patch_area_m2: number | null;
  priority: string | null;
  priority_label: string | null;
  priority_score: number | null;
  boxes: DetectionBox[];
  annotated_image: string;
  created_at: number;
  case_id: number | null;
}

export interface InspectionCreateParams {
  filename: string;
  road_name: string;
  lat: number | null;
  lon: number | null;
  total_defects: number;
  severity_score: number;
  composite_damage_score: number;
  boxes: DetectionBox[];
  annotated_image: string;
  address?: string | null;
  ward?: string | null;
  city?: string | null;
  state?: string | null;
  osm_road_type?: string | null;
}

export interface Contractor {
  id: number;
  name: string;
  specialty: string;
  service_area: string;
  rating: number;
  crew_count: number;
}

export interface Portal {
  code: string;
  name: string;
  authority: string;
  department: string;
  portal_url: string;
  simulated: boolean;
}

export interface BoqLine {
  description: string;
  unit: string;
  quantity: number;
  rate_inr: number;
  amount_inr: number;
}

export interface Boq {
  area_m2: number;
  lines: BoqLine[];
  subtotal_inr: number;
  net_inr: number;
  gst_inr: number;
  total_inr: number;
}

export interface Bid {
  contractor_id: number;
  contractor_name: string;
  specialty: string;
  service_area: string;
  rating: number;
  quoted_inr: number;
  variance_pct: number;
  promised_days: number;
}

export interface Award {
  contractor_id: number;
  contractor_name: string;
  specialty: string;
  rating: number;
  crew_count: number;
  awarded_inr: number | null;
  promised_days: number | null;
  variance_pct: number;
  awarded_at: number | null;
}

export interface Verification {
  filename: string;
  defects_before: number;
  defects_after: number;
  remaining_ratio: number;
  effectiveness_pct: number;
  severity_after: number;
  damage_score_after: number;
  annotated_image: string;
  passed: boolean;
  checked_at: number;
  attempts: number;
}

export interface PipelineEvent {
  id: number;
  case_id: number | null;
  inspection_id: number | null;
  stage: string;
  actor: string;
  title: string;
  detail: string;
  created_at: number;
}

export interface FindingView {
  id: number;
  filename: string;
  road_name: string;
  address: string | null;
  ward: string | null;
  city: string | null;
  road_class: string;
  lat: number | null;
  lon: number | null;
  total_defects: number;
  severity_score: number;
  composite_damage_score: number;
  patch_area_m2: number | null;
  priority: string | null;
  created_at: number;
  case_id: number | null;
  boxes: DetectionBox[];
  annotated_image: string;
}

export interface CaseView {
  id: number;
  status: CaseStatus;
  stage_index: number;
  stage_label: string;
  created_at: number;
  total_potholes: number;
  avg_severity: number;
  severity_label: string;
  severity_hex: string;
  priority: string | null;
  priority_label: string | null;
  priority_score: number | null;
  patch_area_m2: number | null;
  estimate_inr: number | null;
  boq: Boq | null;
  portal: Portal | null;
  tracking_id: string | null;
  routing_note: string | null;
  officer: string | null;
  submitted_at: number | null;
  acknowledged_at: number | null;
  sla_hours: number | null;
  sla_due_at: number | null;
  sla_state: SlaState;
  hours_remaining: number | null;
  breached: boolean;
  tendered_at: number | null;
  bids: Bid[];
  awarded: Award | null;
  repair_progress_pct: number;
  repair_sim_days: number;
  repaired_at: number | null;
  verification: Verification | null;
  verified_at: number | null;
  closed_at: number | null;
  seconds_per_sim_day: number;
  findings: FindingView[];
  events: PipelineEvent[];
}

export interface Stage {
  key: CaseStatus;
  label: string;
  actor: string;
}

export interface PipelineStats {
  total_findings: number;
  unassigned_findings: number;
  total_cases: number;
  stage_counts: Record<string, number>;
  open_cases: number;
  closed_cases: number;
  sla_breached: number;
  sla_at_risk: number;
  potholes_reported: number;
  potholes_repaired: number;
  area_m2_reported: number;
  estimated_inr: number;
  committed_inr: number;
  seconds_per_sim_day: number;
  stages: Stage[];
}

export interface MapPoint {
  id: number;
  road_name: string;
  address: string;
  ward: string;
  road_class: string;
  lat: number;
  lon: number;
  total_defects: number;
  severity: string;
  severity_score: number;
  confidence: number;
  damage_score: number;
  priority: string;
  color_hex: string;
  color_r: number;
  color_g: number;
  color_b: number;
  case_id: number | null;
  case_status: CaseStatus | "UNFILED";
  tracking_id: string | null;
  repaired: boolean;
  logged_at: number;
}

/* ── Completed repairs (before/after record) ─────────────────────────────── */

export interface HandoverNote {
  reference: string;
  statement: string;
  materials: string;
  defect_liability_months: number;
  traffic_reopened_after_hours: number;
  signed_by: string;
}

export interface ChargeLine {
  label: string;
  note: string;
  amount_inr: number;
}

export interface CompletedRepair {
  case_id: number;
  status: CaseStatus;
  tracking_id: string | null;
  portal: Portal | null;

  primary_road: string;
  roads: string[];
  address: string | null;
  ward: string | null;
  lat: number | null;
  lon: number | null;
  road_class: string;
  summary: string;

  before_image: string;
  after_image: string;
  before_filename: string;
  after_filename: string;

  potholes_before: number;
  potholes_after: number;
  effectiveness_pct: number;
  severity_before: number;
  damage_score_before: number;
  damage_score_after: number;
  reinspection_attempts: number;

  patch_area_m2: number;
  priority: string | null;
  priority_label: string | null;

  contractor_name: string;
  contractor_specialty: string;
  contractor_rating: number;
  crew_count: number;
  promised_days: number;
  actual_days: number;
  lifecycle_days: number;

  estimate_inr: number;
  awarded_inr: number;
  savings_inr: number;
  charges: ChargeLine[];
  boq: Boq | null;

  sla_state: SlaState;
  sla_hours: number | null;
  officer: string | null;

  submitted_at: number | null;
  acknowledged_at: number | null;
  awarded_at: number | null;
  repaired_at: number | null;
  verified_at: number | null;
  closed_at: number | null;
  seconds_per_sim_day: number;

  note: HandoverNote;
  note_issued_at: number | null;
}

/* ── Citizen-facing tracker ───────────────────────────────────────────────
   Server-filtered projection of a case: no contractor identity, no money. */

export type CitizenStageKey =
  | "REPORTED"
  | "FILED"
  | "UNDER_REVIEW"
  | "REPAIR_ASSIGNED"
  | "REPAIR_IN_PROGRESS"
  | "VERIFYING"
  | "RESOLVED";

export interface CitizenStage {
  key: CitizenStageKey;
  label: string;
  description: string;
  completed: boolean;
  active: boolean;
  at: number | null;
}

export interface CitizenCaseView {
  case_id: number;
  tracking_id: string | null;
  status: CaseStatus;
  authority: string | null;
  department: string | null;
  road_name: string;
  address: string | null;
  lat: number | null;
  lon: number | null;
  total_potholes: number;
  patch_area_m2: number | null;
  priority: string | null;
  priority_label: string | null;
  reported_at: number;
  stages: CitizenStage[];
  is_resolved: boolean;
  before_image: string;
  after_image: string;
  description: string | null;
  fix_summary: string | null;
}
