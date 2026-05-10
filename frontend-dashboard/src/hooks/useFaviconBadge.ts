import { useEffect, useRef } from 'react';

const BASE_TITLE = 'HallPass Pro Dashboard';
const FAVICON_HREF = '/favicon.png';
const BADGE_SIZE = 64;

export function useFaviconBadge(count: number) {
  const linkRef = useRef<HTMLLinkElement | null>(null);

  useEffect(() => {
    let link = document.querySelector<HTMLLinkElement>('link[rel="icon"]');
    if (!link) {
      link = document.createElement('link');
      link.rel = 'icon';
      document.head.appendChild(link);
    }
    linkRef.current = link;
  }, []);

  useEffect(() => {
    const link = linkRef.current;
    if (!link) return;

    document.title = count > 0 ? `(${count}) ${BASE_TITLE}` : BASE_TITLE;

    if (count <= 0) {
      link.href = FAVICON_HREF;
      return;
    }

    const canvas = document.createElement('canvas');
    canvas.width = BADGE_SIZE;
    canvas.height = BADGE_SIZE;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const img = new Image();
    img.onload = () => {
      ctx.drawImage(img, 0, 0, BADGE_SIZE, BADGE_SIZE);

      const r = 14;
      const cx = BADGE_SIZE - r - 2;
      const cy = r + 2;

      // Red outer circle
      ctx.beginPath();
      ctx.arc(cx, cy, r, 0, 2 * Math.PI);
      ctx.fillStyle = '#ba1a1a';
      ctx.fill();

      // White inner circle
      ctx.beginPath();
      ctx.arc(cx, cy, r * 0.45, 0, 2 * Math.PI);
      ctx.fillStyle = '#ffffff';
      ctx.fill();

      link.href = canvas.toDataURL('image/png');
    };
    img.src = FAVICON_HREF;
  }, [count]);

  useEffect(() => {
    return () => {
      document.title = BASE_TITLE;
      if (linkRef.current) linkRef.current.href = FAVICON_HREF;
    };
  }, []);
}
