import type { ChatMessage, InspectionResult, Recommendation } from "../types";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8000";

async function readJson<T>(response: Response): Promise<T> {
  const data = (await response.json()) as T & { error?: string };
  if (!response.ok || data.error) {
    throw new Error(data.error || `Request failed with ${response.status}`);
  }
  return data as T;
}

export async function inspectImage(file: File): Promise<InspectionResult> {
  const body = new FormData();
  body.append("image", file);

  const response = await fetch(`${API_BASE}/api/inspect`, {
    method: "POST",
    body
  });

  return readJson<InspectionResult>(response);
}

export async function sendChat(messages: ChatMessage[]): Promise<string> {
  const response = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      messages: messages.map(({ role, content }) => ({ role, content }))
    })
  });

  const data = await readJson<{ reply: string }>(response);
  return data.reply;
}

export async function fetchStorageRecommendation(
  fruitName: string,
  freshnessStatus?: string
): Promise<Recommendation> {
  const response = await fetch(`${API_BASE}/api/storage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      fruit_name: fruitName,
      freshness_status: freshnessStatus || ""
    })
  });

  const data = await readJson<{ recommendation: Recommendation }>(response);
  return data.recommendation;
}

export async function getSpotlightFact(fruit: string): Promise<string> {
  const response = await fetch(`${API_BASE}/api/spotlight?fruit=${encodeURIComponent(fruit)}`);
  const data = await readJson<{ fruit: string; fact: string }>(response);
  return data.fact;
}
