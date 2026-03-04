/**
 * Mock data and handler barrel exports.
 *
 * Usage:
 *   import { mockChannels, chatHandlerDefinitions } from '@/mocks';
 */

// Data
export {
  actors,
  mockChannels,
  mockThreads,
  mockMessages,
  getHydratedThread,
} from './data/mock-chat';

// Handlers
export {
  chatHandlerDefinitions,
  generateAgentResponse,
  generateSystemMessage,
  defaultHandlerConfig,
} from './handlers/chat-handlers';

// Types
export type {
  MockHandlerConfig,
  GetThreadsParams,
  CreateThreadBody,
  SendMessageBody,
} from './handlers/chat-handlers';
