/**
 * Simple email and phone validation for forms.
 */
export function isValidEmail(value: string): boolean {
  if (!value || !value.trim()) return true; // optional
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(value.trim());
}

export function emailError(value: string): string {
  if (!value || !value.trim()) return "";
  if (!isValidEmail(value)) return "Enter a valid email address.";
  return "";
}

export function isValidPhone(value: string): boolean {
  if (!value || !value.trim()) return true; // optional
  const digits = value.replace(/\D/g, "");
  return digits.length >= 10;
}

export function phoneError(value: string): string {
  if (!value || !value.trim()) return "";
  if (!isValidPhone(value)) return "Enter a valid phone number (at least 10 digits).";
  return "";
}
