/**
 * Generic router interface. Implemented on top of any {worker}/inference.json. Input/Output are composed at typegen.
 */
export interface ApiTaskQueue {
  [k: string]: unknown;
}
