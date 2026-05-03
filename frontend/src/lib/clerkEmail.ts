/** Clerk placeholder / dev inbox — not meaningful as user-facing contact email */

export function isClerkSyntheticEmail(email: string | null | undefined): boolean {
  if (!email || typeof email !== 'string') return false;
  const e = email.trim().toLowerCase();
  return e.endsWith('@clerk.temp') || e.includes('@clerk.accounts.');
}

/** Local-part before @ for display, unless synthetic — returns null to skip */
export function friendlyEmailPrefix(email: string | null | undefined): string | null {
  if (!email?.trim() || isClerkSyntheticEmail(email)) return null;
  const local = email.split('@')[0]?.trim();
  return local || null;
}
