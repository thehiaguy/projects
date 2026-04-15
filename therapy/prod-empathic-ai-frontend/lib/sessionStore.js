const SESSION_STORAGE_PREFIX = "empathic-ai-session";

function getStorageKey(sessionId) {
  return `${SESSION_STORAGE_PREFIX}:${sessionId}`;
}

export function persistSessionRecord(sessionRecord) {
  if (typeof window === "undefined" || !sessionRecord?.sessionId) {
    return;
  }

  window.sessionStorage.setItem(getStorageKey(sessionRecord.sessionId), JSON.stringify(sessionRecord));
}

export function readSessionRecord(sessionId) {
  if (typeof window === "undefined" || !sessionId) {
    return null;
  }

  const rawValue = window.sessionStorage.getItem(getStorageKey(sessionId));

  if (!rawValue) {
    return null;
  }

  try {
    return JSON.parse(rawValue);
  } catch {
    return null;
  }
}

export function clearSessionRecord(sessionId) {
  if (typeof window === "undefined" || !sessionId) {
    return;
  }

  window.sessionStorage.removeItem(getStorageKey(sessionId));
}

export function updateSessionRecord(sessionId, partialRecord) {
  if (typeof window === "undefined" || !sessionId) {
    return null;
  }

  const currentRecord = readSessionRecord(sessionId) ?? { sessionId };
  const nextRecord = {
    ...currentRecord,
    ...partialRecord,
  };

  persistSessionRecord(nextRecord);
  return nextRecord;
}
