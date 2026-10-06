/**
 * Get the hostname of a URL.
 */
export const hostOf = (url?: string | null): string | undefined => {
  if (!url) return undefined;
  try {
    return new URL(url).hostname;
  } catch {
    return undefined;
  }
};

/**
 * Get a safe href from a URL. Returns `null` for potentially unsafe URLs.
 */
export const safeHref = (url?: string | null): string | null => {
  if (!url) return null;
  try {
    const { protocol } = new URL(url);
    if (protocol !== "http:" && protocol !== "https:") return null;
    return url;
  } catch {
    return null;
  }
};