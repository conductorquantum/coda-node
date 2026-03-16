# Webhooks

After a job completes (or fails), the result is delivered to the Coda
cloud via a signed HTTP POST to the callback URL provided in the
original job message. Every request carries a fresh short-lived JWT
so the cloud can verify the sender.

## Topics

| Document | Summary |
|---|---|
| [delivery.md](delivery.md) | `WebhookClient` — signing, serialization, retry logic, and error handling. |
| [payload-format.md](payload-format.md) | `WebhookPayload` — field definitions and serialization rules. |

## Key Files

| File | Role |
|---|---|
| `src/self_service/server/webhook.py` | `WebhookClient`, `WebhookPayload` |
| `src/self_service/server/auth.py` | `sign_token()` used for per-request JWT signing |

## Cloud Counterpart

| Cloud File | Role |
|---|---|
| `coda-webapp/app/api/internal/qpu/webhook/route.ts` | Receives and processes webhook POST requests. |

## Flow

```
Consumer                  WebhookClient                 Coda Cloud
   │                           │                            │
   │── send_result(url, payload)──►                         │
   │                           │── sign JWT ──────►         │
   │                           │── POST url        ──────► │
   │                           │   Authorization: Bearer <jwt>
   │                           │   Content-Type: application/json
   │                           │   { job_id, status, counts, ... }
   │                           │                     ◄───── │  200 OK
   │                     ◄─────│                            │
   │                           │                            │
   │   (on 5xx or transport error)                          │
   │                           │── backoff ──────►          │
   │                           │── retry POST     ──────► │
```
