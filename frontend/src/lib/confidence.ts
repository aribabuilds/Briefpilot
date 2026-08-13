// Buckets a field's raw [0,1] confidence into three tiers a user can act on
// at a glance, instead of having to interpret a bare percentage (M14).
//
// Thresholds line up with the backend's existing confidence caps rather than
// being independently guessed: source-span linking's UNVERIFIED_CONFIDENCE_CAP
// (backend/app/services/source_span_linking.py) is 0.4, so any unverified
// value lands exactly on the medium/low boundary; validators.py's
// VALIDATION_FAILURE_CONFIDENCE_CAP is 0.2, landing in "low". A verified,
// internally-consistent value normally clears 0.8.
export type ConfidenceTier = "high" | "medium" | "low";

const HIGH_THRESHOLD = 0.8;
const MEDIUM_THRESHOLD = 0.4;

export function confidenceTier(confidence: number): ConfidenceTier {
  if (confidence >= HIGH_THRESHOLD) return "high";
  if (confidence >= MEDIUM_THRESHOLD) return "medium";
  return "low";
}

const TIER_LABELS: Record<ConfidenceTier, string> = {
  high: "High confidence",
  medium: "Medium confidence",
  low: "Low confidence",
};

export function confidenceTierLabel(tier: ConfidenceTier): string {
  return TIER_LABELS[tier];
}
