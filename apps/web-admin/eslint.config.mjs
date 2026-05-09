import { FlatCompat } from "@eslint/eslintrc";

const compat = new FlatCompat();

const config = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    ignores: [".next/**", "node_modules/**", "out/**", "tsconfig.tsbuildinfo"]
  }
];

export default config;
