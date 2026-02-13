/**
 * Copy text to clipboard with fallback for older browsers
 * @param text - Text to copy to clipboard
 * @returns Promise that resolves to true if successful, false otherwise
 */
export async function copyToClipboard(text: string): Promise<boolean> {
  console.debug('[Clipboard] Attempting to copy text to clipboard');

  try {
    // Modern Clipboard API (requires HTTPS)
    await navigator.clipboard.writeText(text);
    console.info('[Clipboard] Text copied successfully using Clipboard API');
    return true;
  } catch (err) {
    console.debug('[Clipboard] Clipboard API failed, trying fallback method:', err);

    // Fallback for older browsers or HTTP contexts
    try {
      const textarea = document.createElement('textarea');
      textarea.value = text;
      textarea.style.position = 'fixed';
      textarea.style.opacity = '0';
      document.body.appendChild(textarea);
      textarea.select();
      const success = document.execCommand('copy');
      document.body.removeChild(textarea);

      if (success) {
        console.info('[Clipboard] Text copied successfully using fallback method');
      } else {
        console.error('[Clipboard] Failed to copy text using fallback method');
      }

      return success;
    } catch (fallbackErr) {
      console.error('[Clipboard] Fallback copy method failed:', fallbackErr);
      return false;
    }
  }
}
