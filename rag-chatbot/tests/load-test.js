import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
export const errorRate = new Rate('errors');
export const responseTime = new Trend('response_time');

// Test configuration
export const options = {
  stages: [
    { duration: '2m', target: 100 }, // Ramp up to 100 users
    { duration: '5m', target: 100 }, // Stay at 100 users
    { duration: '2m', target: 200 }, // Ramp up to 200 users
    { duration: '5m', target: 200 }, // Stay at 200 users
    { duration: '2m', target: 500 }, // Ramp up to 500 users (target)
    { duration: '10m', target: 500 }, // Stay at 500 users
    { duration: '2m', target: 0 }, // Ramp down to 0 users
  ],
  thresholds: {
    http_req_duration: ['p(95)<2000'], // 95% of requests must complete below 2s
    http_req_failed: ['rate<0.1'], // Error rate must be below 10%
    errors: ['rate<0.1'], // Custom error rate
    response_time: ['p(95)<2000'], // 95% of responses below 2s
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:5000';
const API_URL = `${BASE_URL}/api`;
const SOCKET_URL = __ENV.SOCKET_URL || 'ws://localhost:5000';

// Test data
const testMessages = [
  "What is the main topic of the document?",
  "Can you summarize the key points?",
  "What are the important findings?",
  "How does this relate to the previous discussion?",
  "Can you provide more details about this topic?",
  "What are the recommendations mentioned?",
  "How can I apply this information?",
  "What are the limitations discussed?",
  "Can you explain this concept in simple terms?",
  "What are the next steps mentioned?"
];

export default function () {
  // Test 1: Health Check
  const healthResponse = http.get(`${BASE_URL}/health`);
  check(healthResponse, {
    'health check status is 200': (r) => r.status === 200,
    'health check response time < 500ms': (r) => r.timings.duration < 500,
  });
  errorRate.add(healthResponse.status !== 200);
  responseTime.add(healthResponse.timings.duration);

  // Test 2: Chat API
  const randomMessage = testMessages[Math.floor(Math.random() * testMessages.length)];
  const chatPayload = JSON.stringify({
    message: randomMessage,
    session_id: `load_test_${__VU}_${__ITER}`
  });

  const chatResponse = http.post(`${API_URL}/chat`, chatPayload, {
    headers: { 'Content-Type': 'application/json' },
  });

  check(chatResponse, {
    'chat API status is 200': (r) => r.status === 200,
    'chat API response time < 5s': (r) => r.timings.duration < 5000,
    'chat API returns answer': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body.answer && body.answer.length > 0;
      } catch (e) {
        return false;
      }
    },
  });
  errorRate.add(chatResponse.status !== 200);
  responseTime.add(chatResponse.timings.duration);

  // Test 3: Document List API
  const docsResponse = http.get(`${API_URL}/documents`);
  check(docsResponse, {
    'documents API status is 200': (r) => r.status === 200,
    'documents API response time < 1s': (r) => r.timings.duration < 1000,
  });
  errorRate.add(docsResponse.status !== 200);
  responseTime.add(docsResponse.timings.duration);

  // Test 4: Chat History API
  const historyResponse = http.get(`${API_URL}/chat/history/load_test_${__VU}_${__ITER}`);
  check(historyResponse, {
    'chat history API status is 200': (r) => r.status === 200,
    'chat history API response time < 1s': (r) => r.timings.duration < 1000,
  });
  errorRate.add(historyResponse.status !== 200);
  responseTime.add(historyResponse.timings.duration);

  // Random sleep between requests (1-3 seconds)
  sleep(Math.random() * 2 + 1);
}

export function handleSummary(data) {
  return {
    'load-test-results.json': JSON.stringify(data, null, 2),
    stdout: `
Load Test Results Summary:
=======================
- Total Requests: ${data.metrics.http_reqs.values.count}
- Failed Requests: ${data.metrics.http_req_failed.values.count}
- Error Rate: ${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)}%
- Average Response Time: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms
- 95th Percentile Response Time: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms
- Requests per Second: ${data.metrics.http_reqs.values.rate.toFixed(2)}
- Data Transferred: ${(data.metrics.data_sent.values.count / 1024 / 1024).toFixed(2)}MB
- Data Received: ${(data.metrics.data_received.values.count / 1024 / 1024).toFixed(2)}MB

Thresholds:
- Response Time (95th percentile): ${data.metrics.http_req_duration.values['p(95)'] < 2000 ? 'PASS' : 'FAIL'} (${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms)
- Error Rate: ${data.metrics.http_req_failed.values.rate < 0.1 ? 'PASS' : 'FAIL'} (${(data.metrics.http_req_failed.values.rate * 100).toFixed(2)}%)
    `,
  };
}
