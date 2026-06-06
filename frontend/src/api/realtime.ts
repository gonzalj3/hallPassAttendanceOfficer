// WebSocket subscription hook for the realtime endpoint.
// Defaults to ws://localhost:8731 in dev; override with VITE_WS_URL on
// the deployed build (use wss:// when the page is served over HTTPS).

import { useEffect, useRef } from 'react';
import type { RealtimeEnvelope } from './types';

function deriveWsBase(): string {
  // Same-origin WebSocket. vite proxy in dev and netlify rewrites in
  // prod both forward /v1/realtime to the FastAPI backend. No env vars.
  if (typeof window === 'undefined') return '';
  const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${scheme}://${window.location.host}`;
}

const WS_BASE = deriveWsBase();

export interface UseRealtimeOptions {
  /** Channels to LISTEN on, e.g. ["school:<uuid>", "class:<uuid>"]. */
  channels: string[];
  onEvent: (envelope: RealtimeEnvelope) => void;
  /** Optional connection lifecycle callback for debug logging / banners. */
  onStatus?: (status: 'open' | 'closed' | 'error') => void;
}

/**
 * Subscribe to realtime events on the given channels. Reconnects with
 * linear backoff if the connection drops while the component is mounted.
 *
 * No-ops when `channels` is empty so callers can safely pass conditional
 * channel arrays during initial render.
 */
export function useRealtime({ channels, onEvent, onStatus }: UseRealtimeOptions): void {
  // Pin handlers in refs so reconnects don't capture stale closures.
  const onEventRef = useRef(onEvent);
  const onStatusRef = useRef(onStatus);
  onEventRef.current = onEvent;
  onStatusRef.current = onStatus;

  // Memoise the channel set so a same-content array doesn't reconnect.
  const channelKey = channels.slice().sort().join('|');

  useEffect(() => {
    if (!channelKey) return;
    const channelList = channelKey.split('|');
    const query = channelList.map((c) => `channel=${encodeURIComponent(c)}`).join('&');
    const url = `${WS_BASE}/v1/realtime?${query}`;

    let cancelled = false;
    let retry = 0;
    let socket: WebSocket | null = null;

    const connect = () => {
      if (cancelled) return;
      socket = new WebSocket(url);
      socket.onopen = () => {
        retry = 0;
        onStatusRef.current?.('open');
      };
      socket.onmessage = (event) => {
        try {
          const envelope = JSON.parse(event.data) as RealtimeEnvelope;
          onEventRef.current(envelope);
        } catch {
          // Drop malformed frames — server-side bug, not the client's job.
        }
      };
      socket.onerror = () => onStatusRef.current?.('error');
      socket.onclose = () => {
        onStatusRef.current?.('closed');
        if (cancelled) return;
        retry += 1;
        const delay = Math.min(retry * 500, 5000);
        setTimeout(connect, delay);
      };
    };

    connect();
    return () => {
      cancelled = true;
      socket?.close();
    };
  }, [channelKey]);
}
