import { createServer, type IncomingMessage, type ServerResponse } from 'node:http';
import { randomBytes } from 'node:crypto';
import { router } from './router';
import type { Env } from './index';

function resolveEnv(): Env {
  let token = process.env.SECRET_AUTH_TOKEN;
  if (!token) {
    const artifactPath = require('path').join(process.cwd(), 'dist', 'router-flux2', 'dev.env');
    if (require('fs').existsSync(artifactPath)) {
      const content = require('fs').readFileSync(artifactPath, 'utf8');
      const match = content.match(/^SECRET_AUTH_TOKEN=([^\n]*)/m);
      if (match) token = match[1];
    }
    if (!token) {
      token = randomBytes(32).toString('base64url');
      process.env.SECRET_AUTH_TOKEN = token;
      console.log(`SECRET_AUTH_TOKEN=${token}`);
    }
  }
  return { SECRET_AUTH_TOKEN: token };
}
