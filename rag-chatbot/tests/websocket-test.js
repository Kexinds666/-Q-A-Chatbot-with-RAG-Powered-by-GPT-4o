import ws from 'k6/ws';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
export const wsErrorRate = new Rate('ws_errors');
export const wsResponseTime = new Trend('ws_response_time');
export const wsConnections = new Trend('ws_connections');

// Test configuration
export const options = {
  stages: [
    { duration: '1m', target: 50 }, // Ramp up to 50 WebSocket connections
    { duration: '3m', target: 50 }, // Stay at 50 connections
    { duration: '1m', target: 100 }, // Ramp up to 100 connections
    { duration: '5m', target: 100 }, // Stay at 100 connections
    { duration: '1m', target: 0 }, // Ramp down to 0 connections
  ],
  thresholds: {
    ws_errors: ['rate<0.1'], // WebSocket error rate must be below 10%
    ws_response_time: ['p(95)<3000'], // 95% of responses below 3s
  },
};

const SOCKET_URL = __ENV.SOCKET_URL || 'ws://localhost:5000';
const testMessages = [
  "Hello, can you help me?",
  "What documents are available?",
  "Can you summarize the main points?",
  "What are the key findings?",
  "How can I use this information?",
];

export default function () {
  const sessionId = `ws_test_${__VU}_${__ITER}`;
  
  ws.connect(SOCKET_URL, {}, function (socket) {
    wsConnections.add(1);
    
    socket.on('open', function () {
      console.log(`WebSocket connection opened for VU ${__VU}`);
      
      // Send test messages
      testMessages.forEach((message, index) => {
        setTimeout(() => {
          const startTime = Date.now();
          
          socket.send(JSON.stringify({
            content: message,
            session_id: sessionId
          }));
          
          // Listen for response
          socket.on('message', function (data) {
            const responseTime = Date.now() - startTime;
            wsResponseTime.add(responseTime);
            
            try {
              const response = JSON.parse(data);
              check(response, {
                'WebSocket response has content': (r) => r.content && r.content.length > 0,
                'WebSocket response has id': (r) => r.id,
                'WebSocket response time < 5s': () => responseTime < 5000,
              });
            } catch (e) {
              wsErrorRate.add(1);
            }
          });
          
        }, index * 2000); // Send messages every 2 seconds
      });
    });
    
    socket.on('error', function (e) {
      console.error(`WebSocket error for VU ${__VU}:`, e);
      wsErrorRate.add(1);
    });
    
    socket.on('close', function () {
      console.log(`WebSocket connection closed for VU ${__VU}`);
    });
    
    // Keep connection alive for the test duration
    sleep(30);
    
    socket.close();
  });
}
