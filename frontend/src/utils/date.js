import { formatDistanceToNow, parseISO, format } from 'date-fns';

/**
 * Format a date string (ISO) to a relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(dateString) {
  try {
    const date = parseISO(dateString);
    return formatDistanceToNow(date, { addSuffix: true });
  } catch (error) {
    return dateString || '';
  }
}

/**
 * Format a date to a readable string
 */
export function formatDate(dateString) {
  try {
    const date = parseISO(dateString);
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (error) {
    return dateString || '';
  }
}

/**
 * Format a date and time
 */
export function formatDateTime(dateString) {
  try {
    const date = parseISO(dateString);
    return format(date, 'MMM d, yyyy h:mm a');
  } catch (error) {
    return dateString || '';
  }
}

/**
 * Format a date for input[type=datetime-local]
 */
export function formatDateTimeLocal(dateString) {
  try {
    const date = parseISO(dateString);
    const offset = date.getTimezoneOffset() * 60000; // offset in milliseconds
    const localISOTime = new Date(date - offset).toISOString().slice(0, 16);
    return localISOTime;
  } catch (error) {
    return dateString || '';
  }
}

/**
 * Get color for task priority
 */
export function getPriorityColor(priority) {
  switch ((priority || '').toLowerCase()) {
    case 'high':
      return 'text-red-600 dark:text-red-400';
    case 'medium':
      return 'text-yellow-600 dark:text-yellow-400';
    case 'low':
      return 'text-green-600 dark:text-green-400';
    default:
      return 'text-gray-600 dark:text-gray-400';
  }
}

/**
 * Get color for task status
 */
export function getStatusColor(status) {
  switch ((status || '').toLowerCase()) {
    case 'completed':
    case 'done':
      return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
    case 'in progress':
    case 'in_progress':
      return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
    case 'pending':
      return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
    case 'cancelled':
      return 'bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200';
    default:
      return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
  }
}

/**
 * Check if a task is overdue
 */
export function isOverdue(dueDate) {
  if (!dueDate) return false;
  try {
    const due = parseISO(dueDate);
    const now = new Date();
    return due < now;
  } catch (error) {
    return false;
  }
}
