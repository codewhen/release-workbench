/** Reject incomplete visible form edits instead of silently saving their previous value. */
export function assertFormValidity(): void {
  const invalid = document.querySelector<
    HTMLInputElement | HTMLTextAreaElement
  >("input:invalid,textarea:invalid");
  if (invalid) {
    invalid.focus();
    invalid.reportValidity();
    throw Error("Fix invalid fields before saving or running.");
  }
}
