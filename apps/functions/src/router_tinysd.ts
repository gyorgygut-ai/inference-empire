import { createRouter } from "./_shared/router"
import { api as tinysdApi } from "@packages/schemas/tiny_sd/schema"
import { readConfig, type RouterEnv } from "./_shared/config"

const router = createRouter(tinysdApi, "", { readConfig })

export default {
  fetch(request: Request, env: RouterEnv): Promise<Response> {
    return router.fetch(request, env)
  },
}
