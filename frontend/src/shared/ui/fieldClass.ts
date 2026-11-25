/**
 * Classes shared by native input fields (text, password, dropdown). A field with
 * `aria-invalid` changes its frame: the state is never carried by color alone.
 */
export const fieldClass =
  "h-8 w-full min-w-0 rounded-lg border border-border bg-background px-2.5 text-sm outline-none " +
  "focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring " +
  "disabled:cursor-not-allowed disabled:opacity-50 " +
  "aria-invalid:border-destructive aria-invalid:ring-3 aria-invalid:ring-destructive/20";
