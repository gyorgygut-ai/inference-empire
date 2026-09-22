declare global {
  namespace NodeJS {
    interface ProcessEnv {
      STATUS_STATE: KVNamespace
    }
  }
}

export {}
