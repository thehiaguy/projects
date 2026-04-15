import SessionExperience from "../../components/SessionExperience.jsx";
import { deriveBackendWsBaseUrl, resolveBackendApiBaseUrl } from "../../lib/runtime";

function readSearchParamsValue(searchParams, key) {
  const value = searchParams?.[key];

  if (Array.isArray(value)) {
    return value[0] ?? null;
  }

  return typeof value === "string" ? value : null;
}

function isValidSessionId(value) {
  return Boolean(value && /^[A-Za-z0-9:_-]+$/.test(value));
}

export default async function SessionPage({ searchParams }) {
  const resolvedSearchParams = await searchParams;
  const sessionId = readSearchParamsValue(resolvedSearchParams, "sessionId");
  const apiBaseUrl = resolveBackendApiBaseUrl();
  const wsBaseUrl = deriveBackendWsBaseUrl(apiBaseUrl);
  const humeConfigId =
    process.env.HUME_CONFIG_ID ??
    process.env.NEXT_PUBLIC_HUME_CONFIG_ID ??
    null;

  if (!isValidSessionId(sessionId)) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[linear-gradient(180deg,#f9faf6,#eef4ff)] px-6">
        <div className="max-w-lg rounded-[2rem] border border-rose-200 bg-white p-8 text-center shadow-[0_20px_45px_rgba(15,23,42,0.08)]">
          <p className="text-xs uppercase tracking-[0.32em] text-slate-500">Invalid session</p>
          <h1 className="mt-3 text-3xl font-semibold text-slate-950">Missing or invalid session ID</h1>
          <p className="mt-4 text-sm leading-6 text-slate-600">
            Start a new backend session from the landing page so the frontend can retrieve the session token and open the authenticated websocket.
          </p>
        </div>
      </main>
    );
  }

  return (
    <SessionExperience
      sessionId={sessionId}
      apiBaseUrl={apiBaseUrl}
      wsBaseUrl={wsBaseUrl}
      humeConfigId={humeConfigId}
    />
  );
}
