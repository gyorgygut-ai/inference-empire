import "@testing-library/jest-dom/vitest"
import type { TestingLibraryMatchers } from "@testing-library/jest-dom/matchers"

// The workspace hoists @testing-library/jest-dom to the root, where its
// `declare module "vitest"` augmentation binds to the root vitest v4 types.
// face-value resolves `vitest` to its nested v5 copy, so matchers are missing
// there. Re-apply the augmentation against the locally resolved vitest.
declare module "vitest" {
  // eslint-disable-next-line @typescript-eslint/no-empty-object-type -- augmentation only re-binds matchers to the local vitest copy
  interface Assertion<R extends void | Promise<void> = void, T = unknown> extends TestingLibraryMatchers<R, T> {}
}

class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
}

global.ResizeObserver = ResizeObserver as unknown as typeof globalThis.ResizeObserver

global.HTMLElement.prototype.scrollTo = () => {}
global.HTMLDivElement.prototype.scrollTo = () => {}
global.Element.prototype.scrollTo = () => {}
