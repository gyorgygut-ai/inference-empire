declare global {
  namespace NodeJS {
    interface ProcessEnv {
      INFERENCE_TOKEN: string;
      INFERENCE_ENDPOINT_ID: string;
      CF_ACCESS_AUD?: string;
      CF_TEAM_DOMAIN?: string;
    }
  }
}

export {}