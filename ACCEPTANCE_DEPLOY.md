This deploy flow must run with generative-ui:face-value:deploy
Clearn root dist artifacts before each run.
Run in foreground. Report every 10 seconds even if no news.

Worker worker-{model}:deploy-{modal|beam} (only for affected)

- dist/worker-{model}/deploy/deploy-modal.env exists, APP_URL=<live-url>
- curl $APP_URL reaches the worker (HTTP from worker, not DNS/refused)

Router router:router-{model}:deploy:

- dist/router/deploy/router-{model}.env exists, APP_URL, SECRET_AUTH_TOKEN non-empty
- curl $APP_URL reaches router
- POST /q no-auth → 401 Unauthorized
- POST /q bad-token → 401 Invalid token
- POST /q good-token → not 401 (500 from unwired provider = separate known failure)

Frontend generative-ui:face-value:deploy:

- dist/generative-ui/deploy/face-value.env exists, ROUTER_FLUX2_APP_URL + token byte-match router artifact
- Next ✓ Ready, GET {deployed vercel url}
- generate-image reads URL + token from env, zero hardcoded values
