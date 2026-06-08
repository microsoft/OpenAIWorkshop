/**
 * Runtime configuration support
 * Priority: window.__CONFIG__ (runtime) > import.meta.env (build-time) > defaults
 * 
 * When served from the same origin as the API (production), use relative URLs.
 * For local dev with separate frontend server, use localhost URLs.
 */
const runtimeConfig = typeof window !== 'undefined' ? window.__CONFIG__ || {} : {};

// Determine if we're running from same origin as API (production mode)
const isSameOrigin = typeof window !== 'undefined' && 
  !window.location.port.includes('5173') && // Not Vite dev server
  !window.location.port.includes('3000');   // Not React dev server

// In production (same origin), use relative URLs. In dev, use localhost.
const defaultBaseUrl = isSameOrigin ? '' : 'http://localhost:8001';
const defaultWsUrl = isSameOrigin 
  ? `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/ws`
  : 'ws://localhost:8001/ws';

/**
 * API configuration constants
 */
export const API_CONFIG = {
  BASE_URL: runtimeConfig.API_BASE_URL || import.meta.env.VITE_API_BASE_URL || defaultBaseUrl,
  WS_URL: runtimeConfig.WS_URL || import.meta.env.VITE_WS_URL || defaultWsUrl,
  ENDPOINTS: {
    ALERTS: '/api/alerts',
    WORKFLOW_START: '/api/workflow/start',
    WORKFLOW_DECISION: '/api/workflow/decision',
    EVENTS_STREAM: '/api/events/stream',
    PRODUCER_STATUS: '/api/producer/status',
    PRODUCER_START: '/api/producer/start',
    PRODUCER_STOP: '/api/producer/stop',
  },
};

/**
 * WebSocket configuration
 */
export const WS_CONFIG = {
  RECONNECT_DELAY: 3000,
  MAX_RECONNECT_ATTEMPTS: 10,
};

/**
 * Application constants
 */
export const APP_CONFIG = {
  TITLE: import.meta.env.VITE_APP_TITLE || 'Fraud Detection Workflow Visualizer',
};

export default {
  API_CONFIG,
  WS_CONFIG,
  APP_CONFIG,
};
