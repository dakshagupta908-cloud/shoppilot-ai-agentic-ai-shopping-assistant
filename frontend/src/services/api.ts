import axios from "axios";

const sessionKey = "shoppilot-session";
let sessionId = localStorage.getItem(sessionKey);
if (!sessionId) {
  sessionId = crypto.randomUUID();
  localStorage.setItem(sessionKey, sessionId);
}

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "http://localhost:8000",
  timeout: 15000,
  headers: { "X-Session-ID": sessionId },
});

type ApiErrorResponse = {
  detail?: string | Array<{ msg?: string }>;
};

export function errorMessage(error: unknown): string {
  if (axios.isAxiosError<ApiErrorResponse>(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) return detail.map((item) => item.msg).filter(Boolean).join("; ");
    return error.message || "The server could not complete that request.";
  }
  if (error instanceof Error) return error.message;
  return "Something went wrong. Please try again.";
}
