#!/usr/bin/env -S npx tsx
import { readFileSync } from 'fs';

function main() {
  const [inputArg, path] = process.argv.slice(2);
  if (!inputArg || !path) {
    console.error('Usage: wait-for-artifact.ts input <path>');
    process.exit(1);
  }
  
  try {
    const content = readFileSync(path, 'utf-8').trim();
    console.log(content);
  } catch (err) {
    console.error(`Error reading ${path}:`, err);
    process.exit(1);
  }
}
main();