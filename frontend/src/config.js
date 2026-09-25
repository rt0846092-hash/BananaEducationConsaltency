/**
 * Office details, set per client in Vercel/Render environment variables so
 * nobody has to hunt through the code for a phone number.
 */
const env = import.meta.env;

export const OFFICE = {
  name: env.VITE_OFFICE_NAME || "Banana Education",
  phone: env.VITE_OFFICE_PHONE || "01-555 1234",
  // What the phone dials: digits with country code, e.g. +97715551234
  phoneTel: env.VITE_OFFICE_PHONE_TEL || "+97715551234",
  email: env.VITE_OFFICE_EMAIL || "hello@banana.demo",
};

// Country code added to local numbers for WhatsApp links (Nepal: 977).
export const DEFAULT_COUNTRY_CODE = env.VITE_DEFAULT_COUNTRY_CODE || "977";

// Shows the demo logins on the sign-in page and the "sample data" footer.
// Never switch this on for a real client.
/* global __DEMO__ */
export const DEMO = __DEMO__;
