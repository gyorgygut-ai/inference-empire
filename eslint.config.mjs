import nxPlugin from "@nx/eslint-plugin";
import * as jsoncParser from "jsonc-eslint-parser";

export default [
  ...nxPlugin.configs["flat/base"],
  {
    ignores: ["**/.next/**", "**/.opencode/**", "**/node_modules/**", "**/dist/**"],
  },
  {
    files: ["apps/**/package.json", "packages/**/package.json", "tools/**/package.json"],
    languageOptions: {
      parser: jsoncParser,
    },
    rules: {
      "@nx/dependency-checks": [
        "error",
        {
          "useLocalPathsForWorkspaceDependencies": true,
        },
      ],
    },
  },
];
