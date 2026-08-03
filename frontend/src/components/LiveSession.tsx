"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import {
  LiveKitRoom,
  RoomAudioRenderer,
  useConnectionState,
  useLocalParticipant,
  useTranscriptions,
} from "@livekit/components-react";
import { ConnectionState } from "livekit-client";
import "@livekit/components-styles";

function LiveCaptions() {
  const transcriptions = useTranscriptions();
  const bottomRef = useRef<HTMLDivElement>(null);

  const visibleLines = useMemo(
    () => transcriptions.filter((entry) => entry.text.trim().length > 0),
    [transcriptions],
  );

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [visibleLines]);

  return (
    <div className="rounded-xl border border-white/10 bg-[var(--panel)] p-4 min-h-48 max-h-80 overflow-y-auto">
      <h2 className="mb-3 text-sm uppercase tracking-wide text-[var(--muted)]">Live captions</h2>
      {visibleLines.length === 0 ? (
        <p className="text-[var(--muted)]">Start speaking to see captions stream here.</p>
      ) : (
        <ul className="space-y-2">
          {visibleLines.map((entry) => {
            const attributes = entry.streamInfo.attributes ?? {};
            const isFinal = attributes["lk.transcription_final"] === "true";
            const segmentId = attributes["lk.segment_id"] ?? entry.streamInfo.id;

            return (
              <li
                key={segmentId}
                className={isFinal ? "text-white" : "text-[var(--muted)] italic"}
              >
                {entry.text}
                {!isFinal ? (
                  <span className="ml-1 inline-block h-3 w-0.5 animate-pulse bg-[var(--accent)]" />
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
      <div ref={bottomRef} />
    </div>
  );
}

function MicControls({ onLeave }: { onLeave: () => void }) {
  const { localParticipant } = useLocalParticipant();
  const connectionState = useConnectionState();
  const [enabled, setEnabled] = useState(true);

  useEffect(() => {
    if (connectionState !== ConnectionState.Connected) {
      return;
    }

    void localParticipant.setMicrophoneEnabled(enabled);
  }, [connectionState, enabled, localParticipant]);

  const statusLabel =
    connectionState === ConnectionState.Connected
      ? "Connected — streaming captions"
      : connectionState === ConnectionState.Connecting
        ? "Connecting..."
        : "Disconnected";

  return (
    <div className="space-y-3">
      <p className="text-sm text-[var(--muted)]">{statusLabel}</p>
      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          onClick={() => setEnabled((value) => !value)}
          className="rounded-lg bg-[var(--accent)] px-4 py-2 font-medium text-white"
        >
          {enabled ? "Mute mic" : "Unmute mic"}
        </button>
        <button
          type="button"
          onClick={onLeave}
          className="rounded-lg border border-white/20 px-4 py-2"
        >
          End session
        </button>
      </div>
    </div>
  );
}

function ConnectedRoom({ onLeave }: { onLeave: () => void }) {
  return (
    <div className="space-y-4">
      <MicControls onLeave={onLeave} />
      <LiveCaptions />
      <RoomAudioRenderer />
    </div>
  );
}

type LiveSessionProps = {
  token: string;
  serverUrl: string;
  onLeave: () => void;
};

export default function LiveSession({ token, serverUrl, onLeave }: LiveSessionProps) {
  return (
    <LiveKitRoom
      token={token}
      serverUrl={serverUrl}
      connect
      audio
      video={false}
      onDisconnected={onLeave}
      data-lk-theme="default"
      className="space-y-4"
    >
      <ConnectedRoom onLeave={onLeave} />
    </LiveKitRoom>
  );
}
