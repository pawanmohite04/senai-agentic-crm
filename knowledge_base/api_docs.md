# API Documentation

## API Versions

API v1 is deprecated and scheduled for retirement on December 31, 2023. API v2 introduces a new authentication header format, paginated responses, webhook signature validation, and workspace-scoped requests.

## Required Headers

API v2 requests require `Authorization`, `X-Workspace-ID`, `Content-Type`, and idempotency headers for mutation endpoints. Missing `X-Workspace-ID` can produce a 403 even when the API key is valid.

## Rate Limits

Standard plans receive 1,000 requests per minute. Pro plans receive 2,500 requests per minute. Enterprise limits are negotiated and can support 10,000 requests per minute or more with written SLA confirmation.

## Webhooks

Webhook endpoints validate signatures and event schema. Failed webhook authorization should return a structured error with the required scope or missing header when safe to disclose.
