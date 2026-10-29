import { Handler } from "@netlify/functions"

// Note: Netlify deploys this function at the endpoint /.netlify/functions/hello
export const handler: Handler = async () => (
  {
    statusCode: 200,
    body: JSON.stringify({
      message: `Hello, world!`,
    }),
  }
)
