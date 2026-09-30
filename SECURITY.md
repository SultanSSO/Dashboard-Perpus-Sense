# Security notes

- Do not commit `.env`, camera credentials, stream URLs with embedded secrets, raw video, snapshots, model weights, or runtime output.
- Use read-only CCTV accounts and keep credentials in environment variables or a secret manager.
- Keep real camera catalogs and internal IP metadata outside public repositories.
- Keep `MCP_ENABLE_MUTATIONS=false` unless mutation testing is intentional and local.
- Keep `HERMES_MODEL_API_KEY` outside Git; prefer the active Hermes profile secret environment or a secret manager.
- Treat a custom LLM endpoint as OpenAI-compatible only after `/v1/models` and a minimal chat request succeed.
- Do not expose the local dashboard or MCP server directly to the internet; put authentication and authorization at the gateway.
- Face recognition is intentionally out of scope. Any biometric feature requires policy approval, legal review, DPIA, and access controls.
- Treat inference without ground truth as operational observation, not an accuracy claim.
