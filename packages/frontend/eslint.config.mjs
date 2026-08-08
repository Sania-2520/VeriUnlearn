import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

/**
 * Flat ESLint config for VeriUnlearn frontend.
 *
 * Next.js ships its own recommended rulesets:
 *  - "next/core-web-vitals" — core correctness + performance/SEO essentials
 *  - "next/typescript"     — TS-aware rules for Next.js projects
 *
 * The compat bridge is required because eslint-config-next still publishes
 * legacy (eslintrc-style) presets, while this project runs ESLint 9 (flat
 * config by default). `next lint` picks this file up automatically.
 *
 * Scoped relaxations (documented, mirroring the repository's per-layer
 * mypy overrides):
 *  - src/lib/api/client.ts is the untyped JSON API boundary. Responses are
 *    deliberately `any` so callers can narrow at the boundary; runtime
 *    responses have no statically-known shape. All other modules stay strict.
 *  - jest.config.js is a CommonJS tool config; `require()` is idiomatic there.
 */
const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    ignores: [".next/**", "node_modules/**", "next-env.d.ts", "coverage/**"],
  },
  {
    files: ["src/lib/api/client.ts"],
    rules: {
      "@typescript-eslint/no-explicit-any": "off",
    },
  },
  {
    files: ["jest.config.js"],
    rules: {
      "@typescript-eslint/no-require-imports": "off",
    },
  },
];

export default eslintConfig;
