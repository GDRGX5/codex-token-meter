# Contributing

Thank you for helping improve Codex Token Meter.

1. Fork the repository and create a focused branch.
2. Keep the runtime dependency-free unless a dependency solves a clear,
   documented need.
3. Never add sample conversation content, authentication files, or real Codex
   session logs to tests or issues.
4. Run `python -m unittest discover -s tests -v` before opening a pull request.
5. Describe user-visible changes in both `README.md` and `README.zh-TW.md` when
   appropriate.

Pricing updates should cite an official OpenAI model page in `prices.json` and
update the top-level `updated` date.
