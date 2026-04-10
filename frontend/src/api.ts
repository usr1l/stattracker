import type { GameDetail, TodayGame } from "./types";

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").replace(/\/$/, "");
const LOCAL_DEV_HINT =
  " Local dev expects the frontend to proxy /api to http://127.0.0.1:5001. ngrok is not required.";

function withLocalDevHint(message: string) {
  return `${message}${LOCAL_DEV_HINT}`;
}

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function getTodayGames(): Promise<TodayGame[]> {
  let response: Response;
  const url = `${API_BASE_URL}/api/schedule/today`;

  try {
    response = await fetch(url, {
      cache: "no-store",
    });
  } catch (error) {
    throw new ApiError(
      withLocalDevHint(
        error instanceof Error
          ? `${error.message}. Request URL: ${url}.`
          : `Network request failed while loading today's slate. Request URL: ${url}.`,
      ),
      0,
    );
  }

  const body = (await response.json().catch(() => null)) as TodayGame[] | { error?: string } | null;
  if (!response.ok) {
    const message =
      body && typeof body === "object" && "error" in body && typeof body.error === "string"
        ? body.error
        : "Unable to load today's NBA slate.";
    throw new ApiError(message, response.status);
  }

  if (!Array.isArray(body)) {
    throw new ApiError("Unexpected response shape for today's slate.", 0);
  }

  return body;
}

export async function getGameDetail(gameId: string, date: string): Promise<GameDetail> {
  let response: Response;
  const params = new URLSearchParams({ date });
  const url = `${API_BASE_URL}/api/schedule/games/${gameId}?${params.toString()}`;

  try {
    response = await fetch(url, {
      cache: "no-store",
    });
  } catch (error) {
    throw new ApiError(
      withLocalDevHint(
        error instanceof Error
          ? `${error.message}. Request URL: ${url}.`
          : `Network request failed while loading game detail. Request URL: ${url}.`,
      ),
      0,
    );
  }

  const body = (await response.json().catch(() => null)) as GameDetail | { error?: string } | null;
  if (!response.ok) {
    const message =
      body && typeof body === "object" && "error" in body && typeof body.error === "string"
        ? body.error
        : "Unable to load NBA game detail.";
    throw new ApiError(message, response.status);
  }

  if (!body || typeof body !== "object" || Array.isArray(body)) {
    throw new ApiError("Unexpected response shape for game detail.", 0);
  }

  return body as GameDetail;
}
