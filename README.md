# Codex Token Meter

[Traditional Chinese version](README.zh-TW.md)

I made this tool because I wanted a quick answer to two questions: how many
tokens has Codex used, and what would that usage cost through the API?

It reads the local session logs created by Codex Desktop and Codex CLI, then
groups the numbers by date and model. You can view the result in a terminal or
open the included local dashboard in a browser.

The cost shown here is only an API price estimate. It is not your ChatGPT bill
and it does not affect your subscription limits.

## What it shows

- Input, cached-input, cache-write, output, reasoning, and total tokens
- Daily totals and totals for each model
- Estimated API cost in US dollars (USD)
- English and Traditional Chinese output
- A terminal report, a local web dashboard, and optional JSON output

The tool reads local usage metadata only. It does not display or upload your
conversation text, and it does not need an API key.

## Requirements

- Python 3.10 or newer
- Codex Desktop or Codex CLI session logs on the same computer

No third-party Python packages are required.

## Windows

Download and extract the release ZIP. Do not run the files from inside the ZIP.

For the web dashboard, double-click:

```text
RUN_WEB_DASHBOARD.cmd
```

Your browser should open `http://127.0.0.1:8765`. Keep the terminal window open
while using the dashboard. Press `Ctrl+C` in that window to stop the server.

For a terminal report, double-click `RUN_TOKEN_METER.cmd`, or open a terminal in
the extracted folder and run:

```cmd
RUN_TOKEN_METER.cmd --days 7 --lang en
```

## macOS and Linux

Start the web dashboard:

```bash
python3 chatgpt_usage.py --web
```

Or print a seven-day report in the terminal:

```bash
python3 chatgpt_usage.py --days 7 --lang en
```

## Useful commands

```bash
# Today
python3 chatgpt_usage.py --lang en

# Last 30 days
python3 chatgpt_usage.py --days 30 --lang en

# One date
python3 chatgpt_usage.py --date 2026-08-30 --lang en

# Everything found in the local archive
python3 chatgpt_usage.py --all --lang en

# JSON output
python3 chatgpt_usage.py --days 7 --json
```

Use `--lang en`, `--lang zh-TW`, or `--lang auto`. Auto mode follows the
operating-system language.

## Where the numbers come from

The meter looks for `token_count` records in:

- `~/.codex/sessions`
- `~/.codex/archived_sessions`

Codex stores cumulative token snapshots, and the same snapshot may appear more
than once. The meter removes those duplicates and uses the recorded incremental
usage to avoid counting an entire session again after it is resumed or branched.

Reasoning tokens are already part of output tokens, so they are shown separately
but are not added to the bill a second time. Cached input is also included in the
input total and priced at its cached-input rate when one is available.

## API cost estimate

All estimates are shown in USD. Prices are stored in
[`prices.json`](prices.json), so they can be updated without changing the Python
code. Models that are not in the price file are left unpriced instead of being
assigned a guessed rate.

The estimate covers text tokens only. It does not include separate charges for
tools, web search, computer use, images, audio, video, storage, or regional
processing.

Pricing references:

- [GPT-6.2 Astra, GPT-6.2 Sol, and GPT-6.1 Terra](https://developers.openai.com/api/docs/pricing) use Standard rates and 30-minute cache-write pricing.
- [GPT-6.1 Sol](https://developers.openai.com/api/docs/models/gpt-6.1-sol)
- [GPT-6 Sol](https://developers.openai.com/api/docs/models/gpt-6-sol)
- [GPT-6 Luna](https://developers.openai.com/api/docs/models/gpt-6-luna)
- [GPT-6 Astra](https://developers.openai.com/api/docs/models/gpt-6-astra)
- [GPT-5.6 Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol)
- [GPT-5.6 Terra](https://developers.openai.com/api/docs/models/gpt-5.6-terra)
- [GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna)
- [GPT-5.5](https://developers.openai.com/api/docs/models/gpt-5.5)
- [OpenAI API usage fields](https://developers.openai.com/api/reference/resources/admin/subresources/organization/subresources/usage)

## Limitations

This is a Codex log reader, not an account-wide ChatGPT usage meter. It cannot
count normal ChatGPT web, mobile, or desktop conversations unless that usage is
present in the local Codex JSONL files.

The web dashboard runs through a local Python server because a normal hosted
page cannot automatically read `~/.codex`. The server listens on `127.0.0.1`, so
it is only available from the computer where it is running.

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## License

[MIT](LICENSE)
