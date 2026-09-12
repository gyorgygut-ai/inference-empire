import "@testing-library/jest-dom/vitest"

class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

global.ResizeObserver = ResizeObserver as unknown as typeof globalThis.ResizeObserver
