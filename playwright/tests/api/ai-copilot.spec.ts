import { test, expect } from '@playwright/test';
import { getFirstIntentKey, getFirstLearningTopic } from '../../utils/apiHelpers';

/**
 * app/api/ai/copilot_router.py - prefix /api/v1/ai/copilot, tags=["AI Copilot"]
 * Request/response shapes from app/api/ai/copilot_schemas.py.
 *
 *   POST /ask                                  { question: str, min_length=1 }
 *   GET  /questions
 *   GET  /catalog                              -> { intents: [{ key, question_example }] }
 *   GET  /intents/{intent}/answer
 *   GET  /intents/{intent}/sql
 *   GET  /intents/{intent}/explain
 *   GET  /intents/{intent}/related-tables
 *   GET  /intents/{intent}/business-flow
 *   GET  /executive-summary
 *   GET  /business-insights
 *   GET  /provider-status
 *   GET  /root-cause/failed-orders
 *   GET  /root-cause/duplicate-orders
 *   POST /qa-assistant/generate                { target: str, context?: str, test_types?: string[] }
 *   POST /docs-assistant/generate              { doc_type: str, facts: str, title?: str }
 *   GET  /learning/topics                      -> { topics: [{ topic, title }] }
 *   GET  /learning/topics/{topic}
 *   POST /learning/ask                         { question: str, min_length=1 }
 *
 * All routes are gated by `_require_copilot_enabled` -> 403 if
 * COPILOT_ENABLED=false. Tests treat 403 as an acceptable "feature
 * disabled" outcome rather than a failure, since we do not control the
 * local .env this suite runs against; a 5xx is always a failure.
 */

const BASE = '/api/v1/ai/copilot';

function isAcceptable(status: number) {
  return status === 200 || status === 403 || status === 404;
}

test.describe('AI Copilot - read endpoints @regression', () => {
  test('GET /catalog responds', { tag: '@positive' }, async ({ request }) => {
    const res = await request.get(`${BASE}/catalog`);
    expect(isAcceptable(res.status())).toBeTruthy();
  });

  test('GET /questions responds', { tag: '@positive' }, async ({ request }) => {
    const res = await request.get(`${BASE}/questions`);
    expect(isAcceptable(res.status())).toBeTruthy();
  });

  test('GET /executive-summary responds', { tag: '@positive' }, async ({ request }) => {
    const res = await request.get(`${BASE}/executive-summary`);
    expect(isAcceptable(res.status())).toBeTruthy();
  });

  test('GET /business-insights responds', { tag: '@positive' }, async ({ request }) => {
    const res = await request.get(`${BASE}/business-insights`);
    expect(isAcceptable(res.status())).toBeTruthy();
  });

  test('GET /provider-status responds', { tag: '@positive' }, async ({ request }) => {
    const res = await request.get(`${BASE}/provider-status`);
    expect(isAcceptable(res.status())).toBeTruthy();
  });

  test('GET /root-cause/failed-orders responds', { tag: '@positive' }, async ({ request }) => {
    const res = await request.get(`${BASE}/root-cause/failed-orders`);
    expect(isAcceptable(res.status())).toBeTruthy();
  });

  test('GET /root-cause/duplicate-orders responds', { tag: '@positive' }, async ({ request }) => {
    const res = await request.get(`${BASE}/root-cause/duplicate-orders`);
    expect(isAcceptable(res.status())).toBeTruthy();
  });

  test('GET /learning/topics responds', { tag: '@positive' }, async ({ request }) => {
    const res = await request.get(`${BASE}/learning/topics`);
    expect(isAcceptable(res.status())).toBeTruthy();
  });
});

test.describe('AI Copilot - intent-keyed endpoints (dynamic) @regression', () => {
  test('the four intent detail endpoints resolve for a real catalog key', { tag: '@positive' }, async ({ request }) => {
    const intent = await getFirstIntentKey(request);
    test.skip(!intent, 'COPILOT_ENABLED is likely false, or the catalog is empty - cannot resolve a real intent key.');

    for (const suffix of ['answer', 'sql', 'explain', 'related-tables', 'business-flow']) {
      const res = await request.get(`${BASE}/intents/${intent}/${suffix}`);
      expect(res.status()).toBe(200);
    }
  });

  test('GET /intents/{intent}/answer returns 404 for an unknown intent key', { tag: '@negative' }, async ({ request }) => {
    const res = await request.get(`${BASE}/intents/not-a-real-intent-key/answer`);
    expect([403, 404]).toContain(res.status());
  });

  test('learning/topics/{topic} resolves for a real topic key', { tag: '@positive' }, async ({ request }) => {
    const topic = await getFirstLearningTopic(request);
    test.skip(!topic, 'COPILOT_ENABLED is likely false, or no learning topics are configured.');

    const res = await request.get(`${BASE}/learning/topics/${topic}`);
    expect(res.status()).toBe(200);
  });
});

test.describe('AI Copilot - POST endpoints @regression', () => {
  test('POST /ask with a valid question responds', { tag: '@positive' }, async ({ request }) => {
    const res = await request.post(`${BASE}/ask`, {
      data: { question: 'How many pending orders are there?' },
    });
    expect(isAcceptable(res.status())).toBeTruthy();
    if (res.status() === 200) {
      const body = await res.json();
      expect(body).toHaveProperty('matched');
      expect(body).toHaveProperty('answer_text');
    }
  });

  test('POST /ask rejects a blank question', { tag: '@negative' }, async ({ request }) => {
    const res = await request.post(`${BASE}/ask`, { data: { question: '' } });
    expect([422, 403]).toContain(res.status());
  });

  test('POST /ask rejects a missing question field', { tag: '@negative' }, async ({ request }) => {
    const res = await request.post(`${BASE}/ask`, { data: {} });
    expect([422, 403]).toContain(res.status());
  });

  test('POST /learning/ask with a valid question responds', { tag: '@positive' }, async ({ request }) => {
    const res = await request.post(`${BASE}/learning/ask`, {
      data: { question: 'How does order creation work?' },
    });
    expect(isAcceptable(res.status())).toBeTruthy();
  });

  test('POST /learning/ask rejects a blank question', { tag: '@negative' }, async ({ request }) => {
    const res = await request.post(`${BASE}/learning/ask`, { data: { question: '' } });
    expect([422, 403]).toContain(res.status());
  });

  test('POST /qa-assistant/generate with a valid target responds', { tag: '@positive' }, async ({ request }) => {
    const res = await request.post(`${BASE}/qa-assistant/generate`, {
      data: { target: 'POST /api/v1/orders', context: 'Creates a new order.' },
    });
    expect(isAcceptable(res.status())).toBeTruthy();
  });

  test('POST /qa-assistant/generate rejects a missing target', { tag: '@negative' }, async ({ request }) => {
    const res = await request.post(`${BASE}/qa-assistant/generate`, { data: { context: 'no target given' } });
    expect([422, 403]).toContain(res.status());
  });

  test('POST /docs-assistant/generate with valid fields responds', { tag: '@positive' }, async ({ request }) => {
    const res = await request.post(`${BASE}/docs-assistant/generate`, {
      data: { doc_type: 'readme_section', facts: 'OMS-360 processes food delivery orders end to end.' },
    });
    expect(isAcceptable(res.status())).toBeTruthy();
  });

  test('POST /docs-assistant/generate rejects a missing facts field', { tag: '@negative' }, async ({ request }) => {
    const res = await request.post(`${BASE}/docs-assistant/generate`, { data: { doc_type: 'readme_section' } });
    expect([422, 403]).toContain(res.status());
  });
});
