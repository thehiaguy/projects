"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { createSession } from "../lib/api";
import { persistSessionRecord } from "../lib/sessionStore";

export default function HomePageClient({ apiBaseUrl }) {
  const router = useRouter();
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState(null);

  const handleStartSession = async () => {
    setIsCreating(true);
    setError(null);

    try {
      const sessionRecord = await createSession({ baseUrl: apiBaseUrl });
      persistSessionRecord(sessionRecord);
      router.push(`/session?sessionId=${encodeURIComponent(sessionRecord.sessionId)}`);
    } catch (nextError) {
      setError(nextError.message ?? "Unable to create a session.");
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <main className="min-h-screen bg-[radial-gradient(circle_at_top,_rgba(244,201,93,0.22),_transparent_24%),linear-gradient(180deg,#fcfaf5,#eef5ff)] px-6 py-10 text-slate-950 md:px-10">
      <div className="mx-auto grid min-h-[calc(100vh-5rem)] max-w-6xl gap-6 lg:grid-cols-[1.2fr_0.8fr]">
        <section className="rounded-[2.5rem] border border-white/60 bg-[linear-gradient(140deg,rgba(255,255,255,0.88),rgba(255,248,234,0.92))] p-8 shadow-[0_40px_100px_rgba(15,23,42,0.12)] md:p-10">
          <p className="text-xs uppercase tracking-[0.36em] text-slate-500">Empathic AI</p>
          <h1 className="mt-4 max-w-3xl text-5xl font-semibold leading-[1.02] tracking-[-0.04em] text-slate-950">
            Voice session frontend wired for Hume EVI and your backend graph pipeline.
          </h1>
          <p className="mt-6 max-w-2xl text-base leading-7 text-slate-600">
            This route now creates a backend session first, stores the session token locally for websocket auth,
            then routes into the realtime dashboard where the dock controls the Hume call lifecycle.
          </p>

          <div className="mt-8 flex flex-wrap items-center gap-4">
            <button
              type="button"
              onClick={handleStartSession}
              disabled={isCreating}
              className={`rounded-full px-6 py-4 text-sm font-semibold transition ${
                isCreating
                  ? "cursor-not-allowed bg-slate-200 text-slate-500"
                  : "bg-slate-950 text-white hover:bg-slate-800"
              }`}
            >
              {isCreating ? "Creating session..." : "Start new session"}
            </button>
            <p className="text-sm text-slate-500">Backend: {apiBaseUrl}</p>
          </div>

          {error ? (
            <div className="mt-6 rounded-3xl border border-rose-200 bg-rose-50 px-5 py-4 text-sm text-rose-700">
              {error}
            </div>
          ) : null}
        </section>

        <section className="rounded-[2.5rem] border border-slate-200/70 bg-white/80 p-8 shadow-[0_30px_70px_rgba(15,23,42,0.08)]">
          <p className="text-xs uppercase tracking-[0.3em] text-slate-500">What is wired</p>
          <div className="mt-5 space-y-3 text-sm leading-6 text-slate-700">
            <div className="rounded-3xl bg-slate-50 px-4 py-4">
              <code>POST /v1/sessions</code> creates the backend record and persists the returned{" "}
              <code>session_token</code>.
            </div>
            <div className="rounded-3xl bg-slate-50 px-4 py-4">
              The session page opens <code>WS /ws/session/&lt;session_id&gt;?session_token=...</code> and forwards
              finalized Hume events.
            </div>
            <div className="rounded-3xl bg-slate-50 px-4 py-4">
              The dock controls <code>start / stop / mute / end / new</code>, with enablement tied to real
              connection state.
            </div>
            <div className="rounded-3xl bg-slate-50 px-4 py-4">
              Hume user-message prosody scores such as <code>anxiety</code>, <code>distress</code>, and{" "}
              <code>calmness</code> are surfaced live and forwarded to the backend.
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
