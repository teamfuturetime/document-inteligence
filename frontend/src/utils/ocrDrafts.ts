export const OCR_DRAFT_PREFIX = 'vt043:ocr-draft:'
const ownerKey = 'vt043:ocr-draft-owner'

function draftKeys(): string[] {
  try {return Object.keys(sessionStorage).filter(key => key.startsWith(OCR_DRAFT_PREFIX))}
  catch {return []}
}

export const hasOCRDrafts = () => draftKeys().length > 0

export function clearOCRDrafts() {
  try {for (const key of draftKeys()) sessionStorage.removeItem(key)}
  catch {/* Browser storage access restrictions must not keep a logged-out session in the UI. */}
}

export function syncOCRDraftAccount(userId: string) {
  try {
    const previousOwner = sessionStorage.getItem(ownerKey)
    if (previousOwner && previousOwner !== userId) clearOCRDrafts()
    sessionStorage.setItem(ownerKey, userId)
  } catch {/* An unavailable storage backend cannot expose draft text. */}
}
