
/**
 * IMPORTANT: Do not modify this file.
 * This file allows the app to run without bundling in workspace libraries.
 * Must be contained in the ".nx" folder inside the output path.
 */
const Module = require('module');
const path = require('path');
const fs = require('fs');
const originalResolveFilename = Module._resolveFilename;
const distPath = __dirname;
const manifest = [{"module":"@packages/schemas/*","pattern":"./packages/schemas/*"},{"module":"@inference/nx-generate-auth-token","exactMatch":"tools/nx-generate-auth-token/src/index.js","pattern":"./tools/nx-generate-auth-token/src/index.ts"},{"module":"@inference/task-queue-client","exactMatch":"packages/task-queue-client/src/index.js","pattern":"./packages/task-queue-client/src/index.ts"},{"module":"@inference/types","exactMatch":"packages/types/src/index.js","pattern":"./packages/types/src/index.ts"},{"module":"@inference/ui","exactMatch":"packages/ui/src/index.js","pattern":"./packages/ui/src/index.ts"},{"module":"@inference/workspace-plugin","exactMatch":"tools/workspace-plugin/src/index.js","pattern":"./tools/workspace-plugin/src/index.ts"},{"module":"@inference/contracts","exactMatch":"packages/contracts/src/index.js","pattern":"./packages/contracts/src/index.ts"}];

Module._resolveFilename = function(request, parent) {
  let found;
  for (const entry of manifest) {
    if (request === entry.module && entry.exactMatch) {
      const entry = manifest.find((x) => request === x.module || request.startsWith(x.module + "/"));
      const candidate = path.join(distPath, entry.exactMatch);
      if (isFile(candidate)) {
        found = candidate;
        break;
      }
    } else {
      const re = new RegExp(entry.module.replace(/\*$/, "(?<rest>.*)"));
      const match = request.match(re);

      if (match?.groups) {
        const candidate = path.join(distPath, entry.pattern.replace("*", ""), match.groups.rest);
        if (isFile(candidate)) {
          found = candidate;
        }
      }

    }
  }
  if (found) {
    const modifiedArguments = [found, ...[].slice.call(arguments, 1)];
    return originalResolveFilename.apply(this, modifiedArguments);
  } else {
    return originalResolveFilename.apply(this, arguments);
  }
};

function isFile(s) {
  try {
    require.resolve(s);
    return true;
  } catch (_e) {
    return false;
  }
}

// Call the user-defined main.
module.exports = require('./apps/functions/src/main.js');
