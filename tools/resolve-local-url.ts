#!/usr/bin/env -S npx tsx
function main() {
  // Get port from first argument (passed via xargs from piped output)
  const portStr = process.argv[2];
  
  if (!portStr) {
    console.error('Usage: resolve-local-url.ts <port>');
    process.exit(1);
  }
  
  const port = parseInt(portStr.trim(), 10);
  if (isNaN(port) || port < 1 || port > 65535) {
    console.error(`Invalid port: ${portStr}`);
    process.exit(1);
  }
  
  console.log(`http://localhost:${port}`);
}
main();