/**
 * P26.2 Semantic Cache Service
 * LRU in-memory cache for search results (500 entries, 5min TTL)
 * Cache key: SHA256(query + user_id)
 */

import { createHash } from 'node:crypto';

export interface CacheEntry {
  answer: string;
  sources: Array<{
    book: string;
    chapter?: string;
    verse?: string;
    library: 'tripitaka' | 'global_library';
    confidence: number;
  }>;
  confidence: number;
  trace_id: string;
  cached: boolean;
  latency_ms: number;
  timestamp: number;
}

const CACHE_TTL_MS = 5 * 60 * 1000; // 5 minutes
const CACHE_MAX_SIZE = 500;

export class SemanticCache {
  private store = new Map<string, CacheEntry>();

  generateKey(query: string, userId: string): string {
    return createHash('sha256').update(query + userId).digest('hex');
  }

  get(key: string): CacheEntry | null {
    const entry = this.store.get(key);
    if (!entry) return null;
    if (Date.now() - entry.timestamp > CACHE_TTL_MS) {
      this.store.delete(key);
      return null;
    }
    return entry;
  }

  set(key: string, value: CacheEntry): void {
    if (this.store.size >= CACHE_MAX_SIZE) {
      const firstKey = this.store.keys().next().value;
      if (firstKey) this.store.delete(firstKey);
    }
    this.store.set(key, value);
  }

  size(): number {
    return this.store.size;
  }
}

let instance: SemanticCache | null = null;

export function getSemanticCache(): SemanticCache {
  if (!instance) {
    instance = new SemanticCache();
  }
  return instance;
}
