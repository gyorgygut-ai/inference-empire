import { createRouter } from '../router.js';
import type { AddToQueueRequest, AddToQueueResponse, SupResponse } from '../../generated/api-flux2.js';

export const model = 'flux2';
export const router = createRouter<AddToQueueRequest, AddToQueueResponse, SupResponse>();
