export type Basis = "Retrieved fact" | "User assumption" | "Calculated estimate" | "AI interpretation";
export interface Poi { id: string; name: string | null; lat: number; lon: number; distance_m: number; kind: string; segment?: string }
export interface Segment { segment: string; weight: number; count: number; within_500m: number; within_1km: number; weighted: number; nearest_m: number | null; top: Poi[] }
export interface Scenario { multiplier: number; customers_per_day: number; revenue: number; variable_costs: number; fixed_costs: number; profit: number; margin: number; payback_months: number | null; cash_curve: number[] }
export interface Component { key: string; label: string; weight: number; score: number; contribution: number; explanation: string }
export interface SwotItem { text: string; basis: Basis }
export interface AltRow {
  name: string; selected: boolean; place_type: string | null; distance_km: number; lat: number | null; lon: number | null;
  competitors_radius: number; competitors_1km: number; customer_poi_weighted: number; customer_poi_weighted_1km: number; transit_1km: number;
  scores: Record<string, number>; feasibility: number; revenue_medium: number; profit_medium: number; demand_ratio: number;
}
export interface Input {
  business_name: string; category: string; competitor_tag: string; description: string; budget: number; target_customers: string; location: string;
  avg_price: number; customers_per_day: number; working_days: number; variable_cost_pct: number; currency: string;
  expenses: Record<"rent" | "salaries" | "utilities" | "marketing" | "other", number>; poi_radius_km: number; alt_radius_km: number;
}
export interface Analysis {
  id: string; created_at: string; input: Input;
  location: { lat: number; lon: number; display_name: string; address: Record<string, string>; osm_type: string; osm_id: number; source: string };
  category_spec: { competitor_filters: string[]; segments: Record<string, { weight: number; filters: string[] }> };
  retrieval: { retrieved_at: string; elements_returned: number; truncated: boolean; sources: string[] };
  metrics: { radius_km: number; wR: number; w1k: number; cR: number; c1k: number; t1k: number };
  market: {
    radius_km: number; area_km2: number; weighted_total: number; weighted_density_per_km2: number; weighted_within_1km: number; segments: Segment[];
    poi_types: { segment: string; type: string; count: number }[]; pois: Poi[];
    transit: { within_1km: number; total: number; nearest_m: number | null; list: Poi[] };
  };
  competition: {
    total: number; named: number; unnamed: number; density_per_km2: number; within_500m: number; within_1km: number; within_3km: number; nearest_m: number | null;
    pressure: number; rings: { label: string; competitors: number; customer_pois: number }[]; list: Poi[];
  };
  customers: { target_text: string; segments: Segment[]; dominant_segment: string | null; note: string };
  financials: {
    scenarios: Record<"low" | "medium" | "high", Scenario>; fixed_monthly: number; variable_pct: number;
    breakeven_customers_per_day: number | null; breakeven_revenue_monthly: number | null;
    breakeven_curve: { customers_per_day: number; revenue: number; total_cost: number }[];
  };
  feasibility: { score: number; band: string; components: Component[]; note: string };
  alternatives: { status: string; error?: string; radius_km?: number; poi_radius_km?: number; rows: AltRow[]; method?: string; caveats?: string };
  swot: { strengths: SwotItem[]; weaknesses: SwotItem[]; opportunities: SwotItem[]; threats: SwotItem[] };
  highlights: SwotItem[]; limitations: string[];
}
export interface HistoryRow { id: string; created_at: string; business_name: string; category: string; location: string; score: number; has_ai: number }
