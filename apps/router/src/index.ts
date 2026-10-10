import { router } from './router'

export interface Env {
  SECRET_AUTH_TOKEN: string
  ROUTER_FAMILY: string
  BEAM_URL: string
  BEAM_TASK_API: string
  FLASH_URL: string
  FLASH_ENDPOINT: string
}
