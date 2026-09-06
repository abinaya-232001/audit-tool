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
python audit_tool.py
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

## Notes

Originally scoped for Anthropic's API per the case study brief; switched to 
Groq (OpenAI-compatible endpoint) during development for free-tier access. 
The retry/validation logic is provider-agnostic and would work the same way 
with Anthropic or OpenAI's SDKs with minimal changes to the client setup.
