import { assertWsEnvelope } from "./dtos";
import { WS_PACKET_TYPES } from "./constants";

/**
 * Build the backend websocket URL for a session, supporting `ws://` and `wss://`.
 *
 * Expected input:
 * - `params`:
 *   - `wsBaseUrl` (`string`) e.g. `ws://localhost:8000`
 *   - `sessionId` (`string`)
 *
 * Expected output:
 * - `string` fully-qualified websocket URL ending with `/ws/session/{sessionId}`.
 *
 * Purpose:
 * - Prevent route/path construction drift across hooks/components.
 */
export function buildSessionBackendSocketUrl({ wsBaseUrl, sessionId }) {
    if (!wsBaseUrl || !sessionId) {
        throw new Error("buildSessionBackendSocketUrl requires both wsBaseUrl and sessionId.");
    }

    const cleanBaseUrl = wsBaseUrl.replace(/\/$/, "");

    return `${cleanBaseUrl}/ws/session/${sessionId}`;
}

/**
 * Serialize a validated backend client packet into a JSON string for socket transmission.
 *
 * Expected input:
 * - `packet` (`import('./dtos').BackendClientPacket`)
 *
 * Expected output:
 * - `string` JSON payload.
 *
 * Purpose:
 * - Centralize packet serialization and future protocol versioning hooks.
 */
export function serializeBackendClientPacket(packet) {
    if (!packet || typeof packet !== "object") {
        throw new Error("Cannot serialize an invalid or empty packet.");
    }

    try {
        return JSON.stringify(packet);
    } catch (error) {
        throw new Error(`Failed to serialize backend packet: ${error.message}`);
    }
}

/**
 * Parse and validate an incoming backend websocket message into a typed server packet.
 *
 * Expected input:
 * - `rawMessage` (`string`)
 *
 * Expected output:
 * - `import('./dtos').BackendServerPacket`
 *
 * Data contract notes:
 * - Must reject/throw on invalid JSON or unsupported packet `type`.
 * - Should preserve envelope metadata (`session_id`, `sent_at_ms`) for debugging.
 *
 * Purpose:
 * - Enforce the frontend/backend websocket contract at the transport boundary.
 */
export function parseBackendServerPacket(rawMessage) {
    if (!rawMessage || typeof rawMessage !== "string") {
        throw new Error("Invalid transport payload: Expected a string from the WebSocket.");
    }

    let parsedObject;

    try {
        parsedObject = JSON.parse(rawMessage);
    } catch (error) {
        throw new Error(`WebSocket JSON parse error: ${error.message}`);
    }

    // run thru structural validation from dtos.js
    const validatedPacket = assertWsEnvelope(parsedObject);

    // validate type
    const supportedTypes = Object.values(WS_PACKET_TYPES);
    if (!supportedTypes.includes(validatedPacket.type)) {
        throw new Error(`Unsupported WebSocket packet type received: ${validatedPacket.type}`);
    }

    return validatedPacket;
}

/**
 * Compute the next reconnect delay for websocket backoff.
 *
 * Expected input:
 * - `attempt` (`number`) zero-based reconnect attempt count
 * - `config` (`{ baseMs?: number, maxMs?: number, jitter?: boolean }`, optional)
 *
 * Expected output:
 * - `number` delay in milliseconds.
 *
 * Purpose:
 * - Provide consistent reconnect behavior for backend websocket resilience.
 */
export function calculateReconnectDelayMs(attempt, config = {}) {
    const baseMs = config.baseMs || 1000;
    const maxMs = config.maxMs || 30000; 
    const useJitter = config.jitter !== false;

    // make sure the server isn't overloaded with reconnect requests
    let delay = baseMs * Math.pow(2, attempt);

    // dont ddos ourself
    if (useJitter) {
        delay += Math.random() * 1000;
    }

    return Math.min(delay, maxMs);
}