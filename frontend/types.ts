export type ChatRole = "user" | "assistant";

export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  time: string;
};

export type ChatSession = {
  id: string;
  title: string;
  messages: ChatMessage[];
};

export type Recommendation = {
  status?: string;
  temperature?: string;
  humidity?: string;
  shelf_life?: string;
  storage?: string;
  advice?: string;
  ripening_advice?: string;
  nutrition_highlights?: string;
  market_recommendation?: string;
  storage_temperature?: string;
  storage_space?: string;
  market_sale?: string;
  longevity_tip?: string;
  nutrition?: string;
  spoilage_signs?: string;
  possible_causes?: string;
  safe_use?: string;
  disposal?: string;
  prevention?: string;
};

export type SupportedInspection = {
  kind: "supported";
  fruit_name: string;
  detected_fruit: string;
  freshness_status: string;
  predicted_class: string;
  confidence: number;
  raw_vector: number[];
  recommendation: Recommendation;
  recommendation_source?: "local" | "gemini";
  storage_pending?: boolean;
};

export type UnsupportedInspection = {
  kind: "unsupported";
  fruit_name: string;
  message?: string;
};

export type NonFruitInspection = {
  kind: "non_fruit";
  message: string;
};

export type ClassificationResult = {
  kind: "classification";
  fruit_name: string;
  predicted_class: string;
  confidence: number;
  model_scope: string;
  source?: string;
};

export type InspectionResult =
  | SupportedInspection
  | UnsupportedInspection
  | NonFruitInspection
  | ClassificationResult;
