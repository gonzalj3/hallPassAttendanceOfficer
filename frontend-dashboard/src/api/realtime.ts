// WebSocket subscription hook for the realtime endpoint.

import { useEffect, useRef } from 'react';
import type { RealtimeEnvelope } from './types';

function deriveWsBase(): string {
  const explicit = import.meta.env.VITE_WS_URL as string | undefined;
  if (explicit) return explicit;
  const apiBase = import.meta.env.VITE_API_URL as string | undefined;
  if (apiBase) return apiBase.replace(/^http/, 'ws');
  if (typeof window !== 'undefined') {
    const host = window.location.hostname;
    if (host === 'localhost' || host === '127.0.0.1') {
      return 'ws://localhost:8000';
    }
    const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
    return `${scheme}://${window.location.host}`;
  }
  return '';
}

const WS_BASE = deriveWsBase();

export interface UseRealtimeOptions {
  channels: string[];
  onEvent: (envelope: RealtimeEnvelope) => void;
  onStatus?: (status: 'open' | 'closed' | 'error') => void;
}

/** Subscribe to the backend's realtime WS. Reconnects with linear
 *  backoff on drop; no-ops when channels is empty. */
export function useRealtime({ channels, onEvent, onStatus }: UseRealtimeOptions): void {
  const onEventRef = useRef(onEvent);
  const onStatusRef = useRef(onStatus);
  onEventRef.current = onEvent;
  onStatusRef.current = onStatus;

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
          /* drop malformed frames */
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
