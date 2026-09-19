import type { ChatMessage, InspectionResult, Recommendation } from "../types";

// Empty by default: production requests stay on this origin and are proxied by Next.
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "";

async function readJson<T>(response: Response): Promise<T> {
  const data = (await response.json()) as T & { error?: string };
  if (!response.ok || data.error) throw new Error(data.error || `Request failed with ${response.status}`);
  return data as T;
}

export async function getHealth(): Promise<{ ok?: boolean; model_present?: boolean; model_loaded?: boolean; gemini_configured?: boolean; inspection_ready?: boolean; classification_ready?: boolean }> {
  return readJson(await fetch(`${API_BASE}/api/health`, { cache: "no-store" }));
}

export async function classifyImage(file: File): Promise<InspectionResult> {
  const body = new FormData();
  body.append("image", file);
  return readJson(await fetch(`${API_BASE}/api/classify`, { method: "POST", body }));
}

export async function inspectImage(file: File): Promise<InspectionResult> {
  const body = new FormData();
  body.append("image", file);
  return readJson(await fetch(`${API_BASE}/api/inspect`, { method: "POST", body }));
}

export async function sendChat(messages: ChatMessage[]): Promise<string> {
  const data = await readJson<{ reply: string }>(await fetch(`${API_BASE}/api/chat`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages: messages.map(({ role, content }) => ({ role, content })) })
  }));
  return data.reply;
}

export async function fetchStorageRecommendation(fruitName: string, freshnessStatus?: string): Promise<Recommendation> {
  const data = await readJson<{ recommendation: Recommendation }>(await fetch(`${API_BASE}/api/storage`, {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fruit_name: fruitName, freshness_status: freshnessStatus || "" })
  }));
  return data.recommendation;
}

export async function getSpotlightFact(fruit: string): Promise<string> {
  const data = await readJson<{ fruit: string; fact: string }>(await fetch(`${API_BASE}/api/spotlight?fruit=${encodeURIComponent(fruit)}`));
  return data.fact;
}
