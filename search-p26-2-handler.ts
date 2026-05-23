/**
 * P26.2 Search Handler Integration
 * Routes POST /api/search to Smart Classroom :8000/search with dual-source RAG
 * Handles request validation, semantic cache, JWT auth, trace ID propagation
 */

import type { IncomingMessage, ServerResponse } from 'node:http';
import { randomUUID } from 'node:crypto';
import { getSemanticCache } from '../services/semantic-cache.js';
import { getLogger, logApiRequest, logRetryAttempt } from '../utils/logger.js';

const cache = getSemanticCache();
const logger = getLogger();

/**
 * Validates JWT Bearer token from Authorization header
 */
function extractJwtToken(req: IncomingMessage): string | null {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return null;
  }
  return authHeader.slice(7);
}

/**
 * Main search handler
 */
export async function handleSearch(req: IncomingMessage, res: ServerResponse): Promise<boolean> {
  const traceId = `trc_${randomUUID()}`;
  const startTime = Date.now();

  try {
    // 1. Validate JWT
    const jwt = extractJwtToken(req);
    if (!jwt) {
      logger.warn('missing-jwt', { trace_id: traceId, status: 401, error: 'Missing or invalid Authorization header' });
      res.writeHead(401, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Missing or invalid Authorization header', status: 401, trace_id: traceId }));
      return true;
    }

    // 2. Parse request body
    let body = '';
    await new Promise<void>((resolve, reject) => {
      req.on('data', (chunk) => {
        body += chunk.toString();
      });
      req.on('end', () => resolve());
      req.on('error', reject);
    });

    let payload: any;
    try {
      payload = JSON.parse(body);
    } catch (error) {
      logger.warn('invalid-json', { trace_id: traceId, status: 400, error: 'Invalid JSON in request body' });
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Invalid JSON body', status: 400, trace_id: traceId }));
      return true;
    }

    const { query, user_id, channel = 'test' } = payload;

    if (!query || typeof query !== 'string' || query.trim().length === 0) {
      logger.warn('invalid-query', { trace_id: traceId, error: 'Empty or non-string query', status: 400 });
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Query is required and must be non-empty string', status: 400, trace_id: traceId }));
      return true;
    }

    if (!user_id || typeof user_id !== 'string') {
      logger.warn('missing-user-id', { trace_id: traceId, error: 'user_id is required', status: 400 });
      res.writeHead(400, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'user_id is required', status: 400, trace_id: traceId }));
      return true;
    }

    // 3. Check cache
    const cacheKey = cache.generateKey(query, user_id);
    const cachedEntry = cache.get(cacheKey);

    if (cachedEntry) {
      const latency = Date.now() - startTime;
      logger.info('cache-hit', {
        trace_id: traceId,
        user_id,
        query,
        channel,
        latency_ms: latency,
      });
      res.writeHead(200, { 'Content-Type': 'application/json' });
      res.end(
        JSON.stringify({
          answer: cachedEntry.answer,
          sources: cachedEntry.sources,
          confidence: cachedEntry.confidence,
          trace_id: traceId,
          latency_ms: latency,
          cached: true,
        }),
      );
      return true;
    }

    // 4. Call Smart Classroom :8000/search with retry
    const smartClassroomUrl = 'http://localhost:8000/search';
    let lastError: Error | null = null;
    let response: any = null;

    for (let attempt = 1; attempt <= 3; attempt++) {
      try {
        const backoffs = [50, 100, 200];
        if (attempt > 1) {
          await new Promise((resolve) => setTimeout(resolve, backoffs[attempt - 2]));
        }

        const smartClassroomResponse = await fetch(smartClassroomUrl, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${jwt}`,
            'X-Trace-ID': traceId,
          },
          body: JSON.stringify({ query, user_id, channel }),
        });

        if (!smartClassroomResponse.ok) {
          if (smartClassroomResponse.status === 503) {
            lastError = new Error(`Smart Classroom unavailable (attempt ${attempt}/3)`);
            continue;
          }
          throw new Error(`HTTP ${smartClassroomResponse.status}`);
        }

        response = await smartClassroomResponse.json();
        break; // Success, exit retry loop
      } catch (error) {
        lastError = error as Error;
        logRetryAttempt(traceId, attempt, 3, [50, 100, 200][attempt - 2] || 0, (error as Error).message);
        if (attempt === 3) {
          // All retries exhausted
          const latency = Date.now() - startTime;
          logger.error('smart-classroom-exhausted', {
            trace_id: traceId,
            user_id,
            query,
            channel,
            retry_count: 3,
            latency_ms: latency,
            status: 503,
          });
          res.writeHead(503, { 'Content-Type': 'application/json' });
          res.end(
            JSON.stringify({
              error: 'Smart Classroom service unavailable (3 retries exhausted)',
              trace_id: traceId,
              retry_count: 3,
              last_attempt_ms: latency,
              status: 503,
            }),
          );
          return true;
        }
      }
    }

    if (!response) {
      throw lastError || new Error('Unknown error calling Smart Classroom');
    }

    // 5. Validate response schema
    if (!response.answer || !response.sources || response.confidence === undefined) {
      const latency = Date.now() - startTime;
      logger.error('invalid-smart-classroom-response', {
        trace_id: traceId,
        user_id,
        query,
        channel,
        latency_ms: latency,
        status: 502,
        error: 'Missing required fields in Smart Classroom response',
      });
      res.writeHead(502, { 'Content-Type': 'application/json' });
      res.end(JSON.stringify({ error: 'Invalid response from Smart Classroom', status: 502, trace_id: traceId }));
      return true;
    }

    // 6. Cache the response
    const finalLatency = Date.now() - startTime;
    const cacheEntryToStore: any = {
      answer: response.answer,
      sources: response.sources,
      confidence: response.confidence,
      trace_id: traceId,
      cached: false,
      latency_ms: finalLatency,
      timestamp: Date.now(),
    };
    cache.set(cacheKey, cacheEntryToStore);

    // 7. Log successful request
    logApiRequest(traceId, 'search-query', user_id, query, channel, finalLatency, 200, false);

    // 8. Return response
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(
      JSON.stringify({
        answer: response.answer,
        sources: response.sources,
        confidence: response.confidence,
        trace_id: traceId,
        latency_ms: finalLatency,
        cached: false,
      }),
    );

    return true;
  } catch (error) {
    const latency = Date.now() - startTime;
    logger.error('search-handler-error', {
      trace_id: traceId,
      error: error instanceof Error ? error.message : String(error),
      latency_ms: latency,
      status: 500,
    });
    res.writeHead(500, { 'Content-Type': 'application/json' });
    res.end(
      JSON.stringify({
        error: 'Internal server error',
        status: 500,
        trace_id: traceId,
      }),
    );
    return true;
  }
}
