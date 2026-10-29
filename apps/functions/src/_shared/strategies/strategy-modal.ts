import { StrategyUnavailableError, type Strategy } from './strategy'

// The current Modal worker exposes synchronous generate_web, not a task queue.
export const strategyModal: Strategy = {
  async pushToTaskQueue() { throw new StrategyUnavailableError('Modal task queue is not implemented') },
  async fetchTaskStatus() { throw new StrategyUnavailableError('Modal task queue is not implemented') },
}
