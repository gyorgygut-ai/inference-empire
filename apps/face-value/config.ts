import "server-only";
import { envSchema } from "./env.schema.deploy";

const env = envSchema.parse(process.env);

export const config = {
  ROUTER_RESOLVED_URL: new URL('/flux2', env.ROUTER_URL).href,
  ROUTER_GENERATED_AUTH_TOKEN: env.ROUTER_AUTH_TOKEN,
};
