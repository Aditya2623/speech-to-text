"use client";

import { useState } from "react";
import LiveSession from "@/components/LiveSession";
import SessionHistory from "@/components/SessionHistory";
import { createSession, endSession, getToken } from "@/lib/api";

const LIVEKIT_IDENTITY = "user";

export default function HomePage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [roomName, setRoomName] = useState<string | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [serverUrl, setServerUrl] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [historyRefreshKey, setHistoryRefreshKey] = useState(0);

  async function startSession() {
    setLoading(true);
    setError(null);

    try {
      const session = await createSession();
      const tokenResponse = await getToken(LIVEKIT_IDENTITY, session.room_name);

      setSessionId(session.id);
      setRoomName(session.room_name);
      setToken(tokenResponse.token);
      setServerUrl(tokenResponse.url);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start session");
    } finally {
      setLoading(false);
    }
  }

  async function leaveSession() {
    if (sessionId) {
      try {
        await endSession(sessionId);
      } catch {
        // Best-effort cleanup for a personal app.
      }
    }

    setSessionId(null);
    setRoomName(null);
    setToken(null);
    setServerUrl(null);
    setHistoryRefreshKey((key) => key + 1);
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-3xl flex-col gap-8 px-6 py-10">
      <header className="space-y-2">
        <p className="text-sm uppercase tracking-[0.2em] text-[var(--muted)]">Personal STT</p>
        <h1 className="text-4xl font-semibold">Speech to Text</h1>
        <p className="text-[var(--muted)]">
          LiveKit room + Python STT agent. Speak into your mic and watch captions appear in realtime.
        </p>
      </header>

      <section className="space-y-4 rounded-2xl border border-white/10 bg-black/20 p-6">
        {!token || !serverUrl ? (
          <div className="space-y-3">
            <button
              type="button"
              onClick={startSession}
              disabled={loading}
              className="rounded-lg bg-[var(--accent)] px-5 py-3 font-medium text-white disabled:opacity-60"
            >
              {loading ? "Starting..." : "Start new session"}
            </button>
            {error ? <p className="text-red-300">{error}</p> : null}
          </div>
        ) : (
          <div className="space-y-3">
            <p className="text-sm text-[var(--muted)]">
              Room <span className="text-white">{roomName}</span>
            </p>
            <LiveSession token={token} serverUrl={serverUrl} onLeave={leaveSession} />
          </div>
        )}
      </section>

      <section className="space-y-3">
        <h2 className="text-xl font-medium">Transcription history</h2>
        <SessionHistory refreshKey={historyRefreshKey} />
      </section>
    </main>
  );
}
