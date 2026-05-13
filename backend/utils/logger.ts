/**
 * P26.3 Structured Logger with Cloud Logging Integration
 * Uses bunyan for structured JSON logging with automatic Cloud Logging transport on Cloud Run
 * Trace ID correlation: OpenClaw → Smart Classroom → GCP Cloud Logging
 */

import * as bunyan from 'bunyan';
import { CloudLoggingBunyan } from '@google-cloud/logging-bunyan';
import { appendFileSync, mkdirSync } from 'node:fs';
import { join } from 'node:path';

export interface LogContext {
  trace_id: string;
  timestamp?: string;
  operation: string;
  user_id?: string;
  query?: string;
  channel?: string;
  latency_ms?: number;
  status?: number;
  error?: string;
  retry_count?: number;
  cached?: boolean;
  source?: 'tripitaka' | 'global_library';
  [key: string]: any;
}

/**
 * Initialize bunyan logger with Cloud Logging transport on Cloud Run
 */
function initializeBunyan(): bunyan {
  const isCloudRun = !!process.env.CLOUD_RUN_JOB_NAME || !!process.env.K_SERVICE;

  const baseConfig: bunyan.LoggerOptions = {
    name: 'namo-gateway',
    level: process.env.LOG_LEVEL || 'info',
    streams: [],
  };

  // Always write to stdout for Cloud Run
  baseConfig.streams!.push({
    level: 'info',
    stream: process.stdout,
  });

  // Also log to file for local development
  if (!isCloudRun) {
    try {
      mkdirSync('logs', { recursive: true });
      baseConfig.streams!.push({
        level: 'info',
        path: join('logs', 'api_bridge.log'),
      });
    } catch (e) {
      // Ignore if logs directory creation fails
    }
  }

  const logger = bunyan.createLogger(baseConfig);

  // Add Cloud Logging transport on Cloud Run
  if (isCloudRun) {
    try {
      const cloudLogging = new CloudLoggingBunyan({
        projectId: process.env.GCP_PROJECT_ID || 'namo-classroom',
        useMessageField: true,
      });
      cloudLogging.stream('info').on('data', (entry: any) => {
        logger.addStream({
          level: 'info',
          stream: entry,
        });
      });
    } catch (error) {
      console.warn('Failed to initialize Cloud Logging transport:', error);
      // Fallback: continue with stdout/file logging
    }
  }

  return logger;
}

export class StructuredLogger {
  private bunyanLogger: bunyan;
  private traceId: string = '';

  constructor() {
    this.bunyanLogger = initializeBunyan();
  }

  /**
   * Set trace ID for request correlation
   */
  setTraceId(traceId: string): void {
    this.traceId = traceId;
  }

  /**
   * Get current trace ID
   */
  getTraceId(): string {
    return this.traceId;
  }

  /**
   * Log INFO level
   */
  info(operation: string, context: Partial<LogContext> = {}): void {
    this.bunyanLogger.info({ ...context, trace_id: this.traceId, operation });
  }

  /**
   * Log WARN level
   */
  warn(operation: string, context: Partial<LogContext> = {}): void {
    this.bunyanLogger.warn({ ...context, trace_id: this.traceId, operation });
  }

  /**
   * Log ERROR level
   */
  error(operation: string, context: Partial<LogContext> = {}): void {
    this.bunyanLogger.error({ ...context, trace_id: this.traceId, operation });
  }
}

// Singleton instance
let instance: StructuredLogger | null = null;

export function getLogger(): StructuredLogger {
  if (!instance) {
    instance = new StructuredLogger();
  }
  return instance;
}

/**
 * Helper: log request with latency
 */
export function logApiRequest(
  traceId: string,
  operation: string,
  userId: string,
  query: string,
  channel: string,
  latencyMs: number,
  statusCode: number,
  cached: boolean = false,
): void {
  const logger = getLogger();
  logger.setTraceId(traceId);

  if (statusCode >= 400) {
    logger.error(operation, {
      user_id: userId,
      query,
      channel,
      latency_ms: latencyMs,
      status: statusCode,
      cached,
    });
  } else {
    logger.info(operation, {
      user_id: userId,
      query,
      channel,
      latency_ms: latencyMs,
      status: statusCode,
      cached,
    });
  }
}

/**
 * Helper: log retry attempt
 */
export function logRetryAttempt(
  traceId: string,
  attempt: number,
  maxAttempts: number,
  backoffMs: number,
  error?: string,
): void {
  const logger = getLogger();
  logger.setTraceId(traceId);

  logger.warn('retry-attempt', {
    attempt,
    max_attempts: maxAttempts,
    backoff_ms: backoffMs,
    error,
  });
}

/**
 * Helper: log cache statistics
 */
export function logCacheStats(traceId: string, size: number, maxSize: number, hitRate: number): void {
  const logger = getLogger();
  logger.setTraceId(traceId);

  logger.info('cache-stats', {
    cache_size: size,
    cache_max_size: maxSize,
    hit_rate: hitRate.toFixed(2),
  });
}
