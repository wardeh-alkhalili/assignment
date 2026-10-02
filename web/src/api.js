const API_BASE = import.meta.env.VITE_API_BASE || "";

export async function planTrip(payload) {
  const response = await fetch(`${API_BASE}/api/trips/plan/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Could not plan this trip.");
  }
  return data;
}

export async function suggestLocations(query) {
  if (!query || query.trim().length < 3) return [];
  const response = await fetch(
    `${API_BASE}/api/geocode/?q=${encodeURIComponent(query.trim())}`
  );
  if (!response.ok) return [];
  const data = await response.json();
  return data.results || [];
}
