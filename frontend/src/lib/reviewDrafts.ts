import { createContext } from 'react';

// Unscoped pre-auth drafts belong only to the reserved local identity.
export const ReviewIdentityContext = createContext('local');

function ownerPrefix(identity: string) {
  return identity === 'local' ? 'field-review:' : `field-review:user:${identity}:`;
}

export function reviewDraftPrefix(identity: string, documentId: string, runId: string) {
  return `${ownerPrefix(identity)}${documentId}:${runId}:`;
}

export function clearReviewDrafts(identity: string) {
  // Storage may be denied. Isolation also comes from namespaces and the session boundary.
  for (const name of ['localStorage', 'sessionStorage'] as const) {
    try {
      const storage = window[name];
      for (const key of Object.keys(storage)) {
        if (
          key.startsWith(ownerPrefix(identity)) &&
          (identity !== 'local' || !key.startsWith('field-review:user:'))
        )
          storage.removeItem(key);
      }
    } catch {
      // Never fall back to another identity's storage if cleanup is unavailable.
    }
  }
}
