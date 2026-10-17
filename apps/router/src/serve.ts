#!/usr/bin/env -S npx tsx
import { serve } from '@hono/node-server';
import { handle } from './handler.js';
import { envSchema, type Env } from '../env.schema.js';

const portArg = process.argv.find((arg) => arg.startsWith('--port='));
const port = portArg ? portArg.slice('--port='.length) : undefined;
const env: Env = envSchema.parse(port ? { ...process.env, PORT: port } : process.env);

const server = serve({ port: env.PORT, fetch: (request) => handle(request, env) });
server.once('listening', () => console.log(`http://127.0.0.1:${env.PORT}`));
