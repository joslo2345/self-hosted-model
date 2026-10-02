# Decisions

What was chosen, what was rejected, and why. Newest package last.

## Project setup (2026-10-02)

- **Separate repo from Project A.** Project B talks to Project A only through the agent's
  OpenAI-compatible provider settings (`AGENT_BASE_URL`, `AGENT_MODEL`, `AGENT_LLM_API_KEY`).
  Keeping the repos apart proves the "config switch, no code change" claim.
- **$0 spend.** No cloud GPUs, no paid API. Cloud infrastructure is written and validated, never
  applied; cloud and hosted-API costs are calculated from published prices.
- **No hosted CI.** `make check` runs locally before every push, so the repo uses no GitHub
  Actions minutes.
