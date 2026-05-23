const STORAGE_KEY = "knowledge-agent-sessions";

export interface SavedMessage {
  role: "user" | "agent";
  content: string;
  agent?: string;
  timestamp: number;
}

export interface SavedSession {
  id: string;
  title: string;
  messages: SavedMessage[];
  createdAt: number;
  updatedAt: number;
}

export function loadSessions(): SavedSession[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

export function saveSessions(sessions: SavedSession[]): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(sessions));
}

export function saveSession(session: SavedSession): void {
  const sessions = loadSessions().filter((s) => s.id !== session.id);
  sessions.push(session);
  saveSessions(sessions);
}

export function deleteSession(id: string): void {
  const sessions = loadSessions().filter((s) => s.id !== id);
  saveSessions(sessions);
}
