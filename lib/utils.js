/**
 * Utility function to conditionally join class names
 */
function cn(...classes) {
  return classes.filter(Boolean).join(' ');
}

module.exports = { cn };
