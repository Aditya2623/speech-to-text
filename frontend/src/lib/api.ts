const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? "http://localhost:8080";

export type Session = {
  id: string;
  room_name: string;
  created_at: string;
  ended_at: string | null;
};

export type Transcript = {
  id: string;
  session_id: string;
  text: string;
  participant_identity: string;
  start_time: string;
  end_time: string;
  created_at: string;
};

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${backendUrl}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    cache: "no-store",
  });

  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export async function createSession(): Promise<Session> {
  return request<Session>("/sessions", { method: "POST", body: "{}" });
}

export async function listSessions(): Promise<{ items: Session[] }> {
  return request<{ items: Session[] }>("/sessions");
}

export async function getSession(sessionId: string): Promise<Session> {
  return request<Session>(`/sessions/${sessionId}`);
}

export async function endSession(sessionId: string): Promise<Session> {
  return request<Session>(`/sessions/${sessionId}`, {
    method: "PATCH",
    body: JSON.stringify({ ended_at: new Date().toISOString() }),
  });
}

export async function getToken(identity: string, roomName: string): Promise<{ token: string; url: string }> {
  return request<{ token: string; url: string }>("/token", {
    method: "POST",
    body: JSON.stringify({ identity, room_name: roomName }),
  });
}

export async function listTranscripts(sessionId: string): Promise<{ items: Transcript[] }> {
  return request<{ items: Transcript[] }>(`/sessions/${sessionId}/transcripts`);
}

export async function createTranscript(
  sessionId: string,
  data: { text: string; start_time: string; end_time: string },
): Promise<Transcript> {
  return request<Transcript>(`/sessions/${sessionId}/transcripts`, {
    method: "POST",
    body: JSON.stringify({
      text: data.text,
      participant_identity: "user",
      start_time: data.start_time,
      end_time: data.end_time,
    }),
  });
}

export async function updateTranscript(transcriptId: string, text: string): Promise<Transcript> {
  return request<Transcript>(`/transcripts/${transcriptId}`, {
    method: "PATCH",
    body: JSON.stringify({ text }),
  });
}

export async function deleteTranscript(transcriptId: string): Promise<void> {
  return request<void>(`/transcripts/${transcriptId}`, { method: "DELETE" });
}

export async function deleteSession(sessionId: string): Promise<void> {
  return request<void>(`/sessions/${sessionId}`, { method: "DELETE" });
}
