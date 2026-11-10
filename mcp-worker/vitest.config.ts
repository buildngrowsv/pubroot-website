import { defineConfig } from "vitest/config";

// Plain vitest (Node runtime, Web-standard Request/Response/fetch).
// Upstream fetch is mocked in every test: no network access.
export default defineConfig({
  test: {
    include: ["test/**/*.test.ts"],
    environment: "node",
  },
});
