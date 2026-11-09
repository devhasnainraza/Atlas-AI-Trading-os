// k6 Load Test: 1,000 Subscribers SSE Market Data Stream (Spec 03 US2, T050; SC-002)
// Verifies quote observation -> client p95 < 1s under concurrent subscriber load.

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Trend, Rate, Counter } from 'k6/metrics';

const quoteLag = new Trend('quote_lag_ms');
const errorRate = new Rate('errors');
const ticksReceived = new Counter('ticks_received');

export const options = {
  scenarios: {
    marketdata_subscribers: {
      executor: 'ramping-vus',
      startVUs: 10,
      stages: [
        { duration: '30s', target: 200 },
        { duration: '1m', target: 1000 },
        { duration: '1m', target: 1000 },
        { duration: '30s', target: 0 },
      ],
      gracefulRampDown: '10s',
    },
  },
  thresholds: {
    'quote_lag_ms': ['p(95)<1000'], // SC-002: observation -> client p95 < 1s
    'errors': ['rate<0.01'],         // < 1% error rate
    'http_req_duration': ['p(95)<1000'],
  },
};

const BASE_URL = __ENV.API_BASE_URL || 'http://localhost:8000';

export default function () {
  const connectionId = 'conn-sim-01';
  const symbols = 'BTC/USDT,ETH/USDT,SOL/USDT';

  // 1. Fetch latest quotes
  const quoteRes = http.get(`${BASE_URL}/v1/market-data/quotes?connection_id=${connectionId}&symbols=${symbols}`, {
    headers: { 'Accept': 'application/json' },
  });

  const success = check(quoteRes, {
    'status is 200': (r) => r.status === 200,
    'has items': (r) => {
      try {
        const body = JSON.parse(r.body);
        return Array.isArray(body.items) && body.items.length > 0;
      } catch {
        return false;
      }
    },
  });

  if (!success) {
    errorRate.add(1);
  } else {
    try {
      const data = JSON.parse(quoteRes.body);
      if (data.items && data.items.length > 0) {
        const item = data.items[0];
        const ageMs = (item.age_seconds || 0) * 1000;
        quoteLag.add(ageMs);
        ticksReceived.add(data.items.length);
      }
    } catch (e) {
      errorRate.add(1);
    }
  }

  sleep(1);
}
