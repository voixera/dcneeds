export const dynamic = "force-dynamic";

const CONTROL_API_URL = process.env.CONTROL_API_URL;
const CONTROL_API_TOKEN = process.env.CONTROL_API_TOKEN;

export function assertControlConfig() {
  if (!CONTROL_API_URL || !CONTROL_API_TOKEN) {
    return Response.json(
      {
        ok: false,
        error: "CONTROL_API_URL dan CONTROL_API_TOKEN belum diset di environment hosting.",
      },
      { status: 500 },
    );
  }
  return null;
}

export async function callControl(path: string, init: RequestInit = {}) {
  const configError = assertControlConfig();
  if (configError) {
    return configError;
  }

  const response = await fetch(`${CONTROL_API_URL}${path}`, {
    ...init,
    cache: "no-store",
    headers: {
      Authorization: `Bearer ${CONTROL_API_TOKEN}`,
      "Content-Type": "application/json",
      ...(init.headers || {}),
    },
  });

  const text = await response.text();
  let payload: unknown;
  try {
    payload = text ? JSON.parse(text) : {};
  } catch {
    payload = { ok: false, error: text || "Invalid response dari control server." };
  }

  return Response.json(payload, { status: response.status });
}
