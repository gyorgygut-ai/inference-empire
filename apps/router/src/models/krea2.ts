import { createRouter } from '../router.js';
import type { AddToQueueRequest, AddToQueueResponse, SupResponse } from '../../generated/api-krea2.js';

export const model = 'krea2';
export const router = createRouter<AddToQueueRequest, AddToQueueResponse, SupResponse>();
