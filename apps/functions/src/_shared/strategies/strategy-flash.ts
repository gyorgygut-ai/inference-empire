import { StrategyUnavailableError, type Strategy } from './strategy'

// Do not invent queue endpoints for the current Flash worker interface.
export const strategyFlash: Strategy = {
  async pushToTaskQueue() { throw new StrategyUnavailableError('Flash task queue is not implemented') },
  async fetchTaskStatus() { throw new StrategyUnavailableError('Flash task queue is not implemented') },
}
