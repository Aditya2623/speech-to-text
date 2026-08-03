"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import {
  createTranscript,
  deleteSession,
  deleteTranscript,
  getSession,
  listTranscripts,
  updateTranscript,
  type Session,
  type Transcript,
} from "@/lib/api";

function TranscriptItem({
  item,
  onUpdate,
  onDelete,
}: {
  item: Transcript;
  onUpdate: (id: string, text: string) => Promise<void>;
  onDelete: (id: string) => Promise<void>;
}) {
  const [editing, setEditing] = useState(false);
  const [draft, setDraft] = useState(item.text);
  const [saving, setSaving] = useState(false);
  const [deleting, setDeleting] = useState(false);

  async function handleSave() {
    const trimmed = draft.trim();
    if (!trimmed) {
      return;
    }

    setSaving(true);
    try {
      await onUpdate(item.id, trimmed);
      setEditing(false);
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete() {
    if (!confirm("Delete this transcript segment?")) {
      return;
    }

    setDeleting(true);
    try {
      await onDelete(item.id);
    } finally {
      setDeleting(false);
    }
  }

  return (
    <article className="rounded-xl border border-white/10 bg-[var(--panel)] p-4">
      {editing ? (
        <div className="space-y-3">
          <textarea
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            rows={3}
            className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-white outline-none focus:border-[var(--accent)]"
          />
          <div className="flex gap-2">
            <button
              type="button"
              onClick={handleSave}
              disabled={saving || !draft.trim()}
              className="rounded-lg bg-[var(--accent)] px-3 py-1.5 text-sm font-medium text-white disabled:opacity-60"
            >
              {saving ? "Saving..." : "Save"}
            </button>
            <button
              type="button"
              onClick={() => {
                setDraft(item.text);
                setEditing(false);
              }}
              className="rounded-lg border border-white/20 px-3 py-1.5 text-sm"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : (
        <>
          <p className="text-lg">{item.text}</p>
          <p className="mt-2 text-xs text-[var(--muted)]">
            {new Date(item.start_time).toLocaleTimeString()} –{" "}
            {new Date(item.end_time).toLocaleTimeString()}
          </p>
          <div className="mt-3 flex gap-2">
            <button
              type="button"
              onClick={() => setEditing(true)}
              className="rounded-lg border border-white/20 px-3 py-1.5 text-sm"
            >
              Edit
            </button>
            <button
              type="button"
              onClick={handleDelete}
              disabled={deleting}
              className="rounded-lg border border-red-400/30 px-3 py-1.5 text-sm text-red-300 hover:bg-red-400/10 disabled:opacity-60"
            >
              {deleting ? "Deleting..." : "Delete"}
            </button>
          </div>
        </>
      )}
    </article>
  );
}

export default function HistoryPage() {
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const sessionId = params.id;

  const [session, setSession] = useState<Session | null>(null);
  const [transcripts, setTranscripts] = useState<Transcript[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [adding, setAdding] = useState(false);
  const [newText, setNewText] = useState("");
  const [creating, setCreating] = useState(false);
  const [deletingSession, setDeletingSession] = useState(false);

  useEffect(() => {
    if (!sessionId) {
      return;
    }

    Promise.all([getSession(sessionId), listTranscripts(sessionId)])
      .then(([sessionResult, transcriptResult]) => {
        setSession(sessionResult);
        setTranscripts(transcriptResult.items);
      })
      .catch((err: Error) => setError(err.message));
  }, [sessionId]);

  async function handleUpdateTranscript(id: string, text: string) {
    const updated = await updateTranscript(id, text);
    setTranscripts((current) => current.map((item) => (item.id === id ? updated : item)));
  }

  async function handleDeleteTranscript(id: string) {
    await deleteTranscript(id);
    setTranscripts((current) => current.filter((item) => item.id !== id));
  }

  async function handleAddTranscript() {
    const trimmed = newText.trim();
    if (!trimmed || !sessionId) {
      return;
    }

    setCreating(true);
    setError(null);

    const now = new Date().toISOString();

    try {
      const created = await createTranscript(sessionId, {
        text: trimmed,
        start_time: now,
        end_time: now,
      });
      setTranscripts((current) => [...current, created]);
      setNewText("");
      setAdding(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to add transcript");
    } finally {
      setCreating(false);
    }
  }

  async function handleDeleteSession() {
    if (!sessionId || !confirm("Delete this session and all its transcripts?")) {
      return;
    }

    setDeletingSession(true);
    setError(null);

    try {
      await deleteSession(sessionId);
      router.push("/");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete session");
      setDeletingSession(false);
    }
  }

  const fullTranscript = transcripts.map((item) => item.text).join(" ");

  return (
    <main className="mx-auto min-h-screen max-w-3xl px-6 py-10">
      <Link href="/" className="text-sm text-[var(--muted)]">
        ← Back to dashboard
      </Link>

      <div className="mt-6 space-y-6">
        <header className="flex flex-wrap items-start justify-between gap-4">
          <div className="space-y-2">
            <h1 className="text-3xl font-semibold">Transcription history</h1>
            {session ? (
              <p className="text-[var(--muted)]">
                {new Date(session.created_at).toLocaleString()}
                {session.ended_at
                  ? ` · Ended ${new Date(session.ended_at).toLocaleString()}`
                  : " · Active"}
              </p>
            ) : null}
          </div>
          <button
            type="button"
            onClick={handleDeleteSession}
            disabled={deletingSession}
            className="rounded-lg border border-red-400/30 px-4 py-2 text-sm text-red-300 hover:bg-red-400/10 disabled:opacity-60"
          >
            {deletingSession ? "Deleting..." : "Delete session"}
          </button>
        </header>

        {error ? <p className="text-red-300">{error}</p> : null}

        {fullTranscript ? (
          <section className="rounded-xl border border-white/10 bg-black/20 p-4">
            <h2 className="mb-2 text-sm uppercase tracking-wide text-[var(--muted)]">Full transcript</h2>
            <p className="leading-relaxed">{fullTranscript}</p>
          </section>
        ) : null}

        <section className="space-y-3">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-medium">Segments</h2>
            {!adding ? (
              <button
                type="button"
                onClick={() => setAdding(true)}
                className="rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-medium text-white"
              >
                Add segment
              </button>
            ) : null}
          </div>

          {adding ? (
            <div className="space-y-3 rounded-xl border border-white/10 bg-[var(--panel)] p-4">
              <textarea
                value={newText}
                onChange={(event) => setNewText(event.target.value)}
                placeholder="Enter transcript text..."
                rows={3}
                className="w-full rounded-lg border border-white/10 bg-black/20 px-3 py-2 text-white outline-none focus:border-[var(--accent)]"
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={handleAddTranscript}
                  disabled={creating || !newText.trim()}
                  className="rounded-lg bg-[var(--accent)] px-3 py-1.5 text-sm font-medium text-white disabled:opacity-60"
                >
                  {creating ? "Adding..." : "Add"}
                </button>
                <button
                  type="button"
                  onClick={() => {
                    setAdding(false);
                    setNewText("");
                  }}
                  className="rounded-lg border border-white/20 px-3 py-1.5 text-sm"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : null}

          {transcripts.length === 0 ? (
            <p className="text-[var(--muted)]">No saved transcript segments yet.</p>
          ) : (
            transcripts.map((item) => (
              <TranscriptItem
                key={item.id}
                item={item}
                onUpdate={handleUpdateTranscript}
                onDelete={handleDeleteTranscript}
              />
            ))
          )}
        </section>
      </div>
    </main>
  );
}
