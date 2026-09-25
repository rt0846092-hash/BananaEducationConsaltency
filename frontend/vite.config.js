import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  const env = { ...loadEnv(mode, process.cwd(), "VITE_"), ...process.env };
  return {
    plugins: [react()],
    define: {
      // Replaced with a literal true/false at build time, so a production
      // build doesn't just hide the demo logins — it leaves them out of the
      // JavaScript entirely.
      __DEMO__: JSON.stringify(env.VITE_DEMO_MODE === "true"),
    },
  };
});
