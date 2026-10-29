import { createContext, useContext } from 'react';

// The client's gender for the card texts ("בחר" / "בחרי") — the backend adds it to every card's data
const GenderContext = createContext<string | null | undefined>(null);

export const GenderProvider = GenderContext.Provider;

/** g('בחר', 'בחרי') — the feminine form for a woman, the masculine otherwise */
export function useG() {
  const gender = useContext(GenderContext);
  return (m: string, f: string) => (gender === 'female' ? f : m);
}
