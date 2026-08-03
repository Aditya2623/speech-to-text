"use client";

import Link from "next/link";
import { useCallback, useEffect, useState } from "react";
import { deleteSession, listSessions, type Session } from "@/lib/api";

type SessionHistoryProps = {
  refreshKey?: number;
};

function formatSessionLabel(session: Session): string {
  const date = new Date(session.created_at).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
  return `Session · ${date}`;
}

export default function SessionHistory({ refreshKey = 0 }: SessionHistoryProps) {
  const [sessions, setSessions] = useState<Session[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const loadSessions = useCallback(() => {
    listSessions()
      .then((result) => setSessions(result.items))
      .catch((err: Error) => setError(err.message));
  }, []);

  useEffect(() => {
    loadSessions();
  }, [loadSessions, refreshKey]);

  async function handleDelete(sessionId: string) {
    if (!confirm("Delete this session and all its transcripts?")) {
      return;
    }

    setDeletingId(sessionId);
    setError(null);

    try {
      await deleteSession(sessionId);
      setSessions((current) => current.filter((session) => session.id !== sessionId));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete session");
    } finally {
      setDeletingId(null);
    }
  }

  if (error) {
    return <p className="text-red-300">{error}</p>;
  }

  if (sessions.length === 0) {
    return <p className="text-[var(--muted)]">No past sessions yet.</p>;
  }

  return (
    <ul className="space-y-2">
      {sessions.map((session) => (
        <li
          key={session.id}
          className="flex items-start justify-between gap-4 rounded-lg border border-white/10 bg-[var(--panel)] px-4 py-3"
        >
          <div className="min-w-0 flex-1">
            <Link href={`/history/${session.id}`} className="font-medium">
              {formatSessionLabel(session)}
            </Link>
            <p className="text-sm text-[var(--muted)]">
              {session.ended_at
                ? `Ended ${new Date(session.ended_at).toLocaleString()}`
                : "Active"}
            </p>
          </div>
          <button
            type="button"
            onClick={() => handleDelete(session.id)}
            disabled={deletingId === session.id}
            className="shrink-0 rounded-lg border border-red-400/30 px-3 py-1.5 text-sm text-red-300 hover:bg-red-400/10 disabled:opacity-60"
          >
            {deletingId === session.id ? "Deleting..." : "Delete"}
          </button>
        </li>
      ))}
    </ul>
  );
}
