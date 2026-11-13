import { createServer } from 'node:http'

const port = Number(process.env.WORKER_WEBRTC_PORT)

if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error('WORKER_WEBRTC_PORT must be an integer between 1 and 65535')
}

export const server = createServer((_request, response) => {
  response.writeHead(200, { 'content-type': 'text/plain' })
  response.end('ok')
})

server.listen(port, '127.0.0.1')
