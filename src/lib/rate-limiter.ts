// src/lib/rate-limiter.ts
// Redis-backed rate limiter for login attempts (Edge Runtime compatible)

// This uses a simple in-memory fallback + Redis if available
// For production, ensure REDIS_URL is set

const RATE_LIMIT_PREFIX = 'ratelimit:login:';
const MAX_ATTEMPTS = 5;
const WINDOW_MS = 10 * 60 * 1000; // 10 minutes sliding window
const BLOCK_DURATION_MS = 15 * 60 * 1000; // 15 minutes block

interface RateLimitEntry {
  count: number;
  firstAttempt: number;
  blockedUntil?: number;
}

// In-memory fallback (for dev / when Redis unavailable)
const memoryStore = new Map<string, RateLimitEntry>();

let redis: any = null;

async function getRedis() {
  if (redis) return redis;
  if (!process.env.REDIS_URL) return null;
  
  try {
    // Dynamic import for Edge compatibility
    const { createClient } = await import('redis');
    redis = createClient({ url: process.env.REDIS_URL });
    redis.on('error', (err: Error) => console.error('Redis rate-limiter error:', err));
    await redis.connect();
    return redis;
  } catch (e) {
    console.warn('Redis unavailable for rate limiting, using memory fallback:', e);
    return null;
  }
}

function memoryGet(key: string): RateLimitEntry | undefined {
  const entry = memoryStore.get(key);
  if (!entry) return undefined;
  
  const now = Date.now();
  // Clean up expired entries
  if (entry.blockedUntil && entry.blockedUntil < now) {
    memoryStore.delete(key);
    return undefined;
  }
  if (!entry.blockedUntil && now - entry.firstAttempt > WINDOW_MS) {
    memoryStore.delete(key);
    return undefined;
  }
  return entry;
}

function memorySet(key: string, entry: RateLimitEntry) {
  memoryStore.set(key, entry);
}

function memoryDel(key: string) {
  memoryStore.delete(key);
}

export async function checkLoginRateLimit(identifier: string): Promise<{
  allowed: boolean;
  retryAfterSeconds?: number;
}> {
  const key = `${RATE_LIMIT_PREFIX}${identifier}`;
  const now = Date.now();
  
  const r = await getRedis();
  
  if (r) {
    // Redis-backed implementation
    const data = await r.get(key);
    if (data) {
      const entry: RateLimitEntry = JSON.parse(data);
      
      if (entry.blockedUntil && entry.blockedUntil > now) {
        return { allowed: false, retryAfterSeconds: Math.ceil((entry.blockedUntil - now) / 1000) };
      }
      
      // Reset if window expired
      if (now - entry.firstAttempt > WINDOW_MS) {
        await r.del(key);
        return { allowed: true };
      }
      
      return { allowed: true };
    }
    return { allowed: true };
  } else {
    // Memory fallback
    const entry = memoryGet(key);
    if (!entry) return { allowed: true };
    
    if (entry.blockedUntil && entry.blockedUntil > now) {
      return { allowed: false, retryAfterSeconds: Math.ceil((entry.blockedUntil - now) / 1000) };
    }
    
    if (now - entry.firstAttempt > WINDOW_MS) {
      memoryDel(key);
      return { allowed: true };
    }
    
    return { allowed: true };
  }
}

export async function recordFailedLogin(identifier: string): Promise<void> {
  const key = `${RATE_LIMIT_PREFIX}${identifier}`;
  const now = Date.now();
  
  const r = await getRedis();
  
  if (r) {
    const data = await r.get(key);
    let entry: RateLimitEntry;
    
    if (data) {
      entry = JSON.parse(data);
      // Reset if window expired
      if (now - entry.firstAttempt > WINDOW_MS) {
        entry = { count: 0, firstAttempt: now };
      }
    } else {
      entry = { count: 0, firstAttempt: now };
    }
    
    entry.count += 1;
    
    if (entry.count >= MAX_ATTEMPTS) {
      entry.blockedUntil = now + BLOCK_DURATION_MS;
      // TTL = block duration + buffer
      await r.set(key, JSON.stringify(entry), { EX: Math.ceil(BLOCK_DURATION_MS / 1000) + 60 });
    } else {
      await r.set(key, JSON.stringify(entry), { EX: Math.ceil(WINDOW_MS / 1000) + 60 });
    }
  } else {
    // Memory fallback
    const entry = memoryGet(key) || { count: 0, firstAttempt: now };
    entry.count += 1;
    
    if (entry.count >= MAX_ATTEMPTS) {
      entry.blockedUntil = now + BLOCK_DURATION_MS;
      // Auto-cleanup after block
      setTimeout(() => memoryDel(key), BLOCK_DURATION_MS + 60000);
    }
    
    memorySet(key, entry);
  }
}

export async function clearLoginRateLimit(identifier: string): Promise<void> {
  const key = `${RATE_LIMIT_PREFIX}${identifier}`;
  const r = await getRedis();
  if (r) {
    await r.del(key);
  } else {
    memoryDel(key);
  }
}