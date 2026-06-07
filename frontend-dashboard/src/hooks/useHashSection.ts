// Bind a "which section am I on" string to the URL hash so a hard
// refresh keeps the user on the same view. Also wires browser
// back/forward to section changes via the popstate event. No router
// dependency -- the dashboard intentionally stays single-page.

import { useCallback, useEffect, useState } from 'react';

export function useHashSection<T extends string>(
  initial: T,
  valid: readonly T[],
): [T, (next: T) => void] {
  const parseHash = useCallback((): T => {
    if (typeof window === 'undefined') return initial;
    const raw = window.location.hash.replace(/^#/, '');
    return (valid as readonly string[]).includes(raw) ? (raw as T) : initial;
  }, [initial, valid]);

  const [section, setSection] = useState<T>(parseHash);

  const update = useCallback(
    (next: T) => {
      setSection(next);
      if (typeof window === 'undefined') return;
      // pushState (not replaceState) so browser back returns you to the
      // section you were on before, not the address you typed in.
      const target = `#${next}`;
      if (window.location.hash !== target) {
        window.history.pushState({}, '', target);
      }
    },
    [],
  );

  useEffect(() => {
    if (typeof window === 'undefined') return;
    const onPopState = () => setSection(parseHash());
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, [parseHash]);

  return [section, update];
}
