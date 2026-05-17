/**
 * k6: 30 virtual users, each creates a conversation and sends one Chat V2 message.
 *
 * Prerequisites: k6 installed (https://k6.io/docs/get-started/installation/)
 *
 * Run:
 *   BASE_URL=https://your-api.example.com \
 *   BEARER_TOKEN='eyJhbGciOi...' \
 *   k6 run scripts/k6/chat_v2_message.js
 *
 * Optional: TOKENS_CSV=/path/to/file.csv with column token (for multiple accounts).
 * If unset, BEARER_TOKEN is used for every VU.
 *
 * X-Forwarded-For varies per VU to reduce SlowAPI per-IP throttling when testing
 * from a single machine (behavior depends on your reverse proxy).
 */

import http from "k6/http";
import { check, sleep } from "k6";
import { SharedArray } from "k6/data";

const BASE_URL = (__ENV.BASE_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

const tokensFromCsv = (() => {
  const p = __ENV.TOKENS_CSV || "";
  if (!p) return null;
  return new SharedArray("tokens", () =>
    open(p)
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean)
      .map((line) => {
        const parts = line.split(",");
        return parts[parts.length - 1].trim();
      }),
  );
})();

export const options = {
  scenarios: {
    parallel_chat_v2: {
      executor: "shared-iterations",
      vus: 30,
      iterations: 30,
      maxDuration: "15m",
    },
  },
  thresholds: {
    http_req_failed: ["rate<0.5"],
    http_req_duration: ["p(95)<120000"],
  },
};

function bearerForVu(vu) {
  const arr = tokensFromCsv;
  if (arr && arr.length > 0) return arr[(vu - 1) % arr.length];
  const t = __ENV.BEARER_TOKEN || "";
  if (!t) throw new Error("Set BEARER_TOKEN or TOKENS_CSV");
  return t;
}

function spoofIp(vu) {
  return `203.0.113.${((vu - 1) % 250) + 1}`;
}

export default function () {
  const vu = __VU;
  const token = bearerForVu(vu);
  const hdr = {
    Authorization: `Bearer ${token}`,
    "Content-Type": "application/json",
    "X-Forwarded-For": spoofIp(vu),
  };
  const params = { headers: hdr, timeout: "180s" };

  const createRes = http.post(`${BASE_URL}/api/chat/conversations`, JSON.stringify({}), params);
  check(createRes, { "create 200": (r) => r.status === 200 }) ||
    console.error(`create failed vu=${vu} status=${createRes.status} body=${String(createRes.body).slice(0, 400)}`);

  if (createRes.status !== 200) return;

  let convId;
  try {
    convId = JSON.parse(createRes.body).id;
  } catch (e) {
    console.error(`bad JSON vu=${vu}`);
    return;
  }

  const payload = JSON.stringify({
    message: `Load test vu=${vu}`,
    conversation_id: convId,
    language: "he",
  });
  const msgRes = http.post(`${BASE_URL}/api/chat/v2/message`, payload, params);
  check(msgRes, {
    "message 200": (r) => r.status === 200,
  }) ||
    console.error(`message failed vu=${vu} status=${msgRes.status} body=${String(msgRes.body).slice(0, 400)}`);

  sleep(0.3);
}
