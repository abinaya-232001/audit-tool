# AI Document & Code Audit Tool

A Python script that audits code or text using the Groq API (Llama/GPT-OSS models)
and returns structured JSON findings: a summary, identified issues (with type,
description, severity), and recommended fixes.

## Setup

```bash
python -m venv venv
venv\Scripts\Activate.ps1   # Windows PowerShell
pip install -r requirements.txt
```

Set your Groq API key (get one free at https://console.groq.com/keys):

```bash
$env:GROQ_API_KEY = "your-key-here"
```

## Usage

```bash
python audit_tool.py                  # runs a built-in demo example
python audit_tool.py yourfile.py      # audits a specific file
```

## Output schema

```json
{
  "summary": "2-sentence overview of the input.",
  "issues_identified": [
    {
      "type": "Bug | Security Risk | Performance | Style | Other",
      "description": "...",
      "severity": "Low | Medium | High"
    }
  ],
  "recommended_fixes": "Actionable advice for optimization."
}
```

## Error handling

- API failures (auth errors, rate limits, connection issues) are retried up to
  3 times with exponential backoff before returning a graceful fallback response.
- Malformed or non-JSON model output is caught and retried; the script never
  crashes on a bad response.

## Notes on provider choice

The case study lists OpenAI, Anthropic, or AWS Bedrock as example providers. As of
testing (Sept 2026), OpenAI's API requires a billing card on file with no free trial
credits currently offered, and Anthropic's API similarly requires payment setup
upfront. To keep this submission runnable by anyone without a financial commitment,
I used Groq's free-tier API instead — it exposes an OpenAI-compatible chat
completions interface, so the integration pattern (client setup, JSON schema
enforcement, retry logic) is directly transferable to any of the three named
providers with only the client initialization and model name changing.

## Repository contents

- `audit_tool.py` — Task 1: core LLM audit script
- `TASK2.md` — Task 2: user stories and data flow
- `TASK3.md` — Task 3: AWS architecture summary
- `requirements.txt` — Python dependencies