import { createRouter } from "./_shared/router"
import { api as flux2Api } from "@packages/schemas/workers/flux2.schema"
import { readConfig, type RouterEnv } from "./_shared/config"

const router = createRouter(flux2Api, "", { readConfig })

export default {
  fetch(request: Request, env: RouterEnv): Promise<Response> {
    return router.fetch(request, env)
  },
}
