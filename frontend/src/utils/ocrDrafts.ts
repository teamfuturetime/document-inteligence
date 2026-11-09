export const OCR_DRAFT_PREFIX = 'vt043:ocr-draft:'
const ownerKey = 'vt043:ocr-draft-owner'
// Track only whether a mounted editor is dirty. OCR text stays in React state.
const dirtyEditors = new Set<object>()
export function setOCRDraftDirty(editor: object, dirty: boolean) {
  if (dirty) dirtyEditors.add(editor)
  else dirtyEditors.delete(editor)
}

function draftKeys(): string[] {
  try {return Object.keys(sessionStorage).filter(key => key.startsWith(OCR_DRAFT_PREFIX))}
  catch {return []}
}

export const hasOCRDrafts = () => dirtyEditors.size > 0 || draftKeys().length > 0

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
