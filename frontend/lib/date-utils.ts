/**
 * Date and timezone utilities for the Task Tracker frontend.
 *
 * These utilities handle the complex conversion between:
 * - User's local timezone (browser timezone)
 * - UTC timezone (API storage format)
 * - HTML input formats (date, datetime-local)
 *
 * Key principles:
 * - API always expects/returns ISO 8601 UTC strings
 * - User sees dates in their local timezone
 * - Date filters should respect local timezone boundaries
 */

/**
 * Convert a local date (YYYY-MM-DD) to UTC ISO string for API queries.
 * Interprets the date as local timezone, not UTC.
 *
 * Example (PST timezone, GMT-8):
 * - Input: "2026-02-10", endOfDay: false
 * - Output: "2026-02-10T08:00:00.000Z" (PST midnight = UTC 08:00)
 *
 * @param localDate - Date string in YYYY-MM-DD format
 * @param endOfDay - If true, returns end of day (23:59:59.999), otherwise start (00:00:00.000)
 * @returns ISO 8601 string in UTC
 */
export function localDateToUTC(localDate: string, endOfDay: boolean = false): string {
  // CRITICAL: Append "T00:00" to force local timezone parsing
  // new Date("2026-02-10") parses as UTC (wrong!)
  // new Date("2026-02-10T00:00") parses as local time (correct!)
  const date = new Date(`${localDate}T00:00`);

  if (endOfDay) {
    date.setHours(23, 59, 59, 999);
  }

  return date.toISOString();
}

/**
 * Convert UTC datetime string to local datetime string for datetime-local input.
 *
 * HTML datetime-local inputs expect format: "YYYY-MM-DDTHH:mm"
 * This converts API UTC datetime to browser's local time.
 *
 * Example (PST timezone):
 * - Input: "2026-02-10T22:30:00.000Z" (UTC)
 * - Output: "2026-02-10T14:30" (PST 2:30 PM)
 *
 * @param utcDateString - ISO 8601 UTC datetime string
 * @returns Local datetime in format "YYYY-MM-DDTHH:mm"
 */
export function utcToLocalInput(utcDateString: string): string {
  const date = new Date(utcDateString);
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');

  return `${year}-${month}-${day}T${hours}:${minutes}`;
}

/**
 * Convert datetime-local input value to UTC ISO string for API.
 *
 * Datetime-local inputs provide local time without timezone info.
 * This converts to UTC for API storage.
 *
 * Example (PST timezone):
 * - Input: "2026-02-10T14:30" (local time)
 * - Output: "2026-02-10T22:30:00.000Z" (UTC)
 *
 * @param localInput - Datetime string from datetime-local input
 * @returns ISO 8601 string in UTC
 */
export function localInputToUTC(localInput: string): string {
  return new Date(localInput).toISOString();
}

/**
 * Format a UTC datetime string for display.
 *
 * Uses Intl.DateTimeFormat for locale-aware formatting.
 * Automatically converts to user's local timezone.
 *
 * @param utcDateString - ISO 8601 UTC datetime string
 * @param options - Intl.DateTimeFormatOptions for customization
 * @returns Formatted date string in user's locale
 */
export function formatDate(
  utcDateString: string,
  options: Intl.DateTimeFormatOptions = {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: 'numeric',
    minute: '2-digit'
  }
): string {
  return new Date(utcDateString).toLocaleString('en-US', options);
}

/**
 * Check if a task is overdue (matches backend logic).
 *
 * A task is overdue if:
 * - It has a due_date
 * - Status is not 'done', 'backlog', or 'not_needed'
 * - Due date is in the past
 *
 * @param task - Task object with due_date and status
 * @returns True if task is overdue
 */
export function isOverdue(task: { due_date: string | null; status: string }): boolean {
  if (!task.due_date || task.status === 'done' || task.status === 'backlog' || task.status === 'not_needed') {
    return false;
  }
  return new Date(task.due_date) < new Date();
}
