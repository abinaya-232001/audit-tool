import os
import json
import time
import logging
from typing import Optional
from groq import Groq
import groq

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("audit_tool")

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

SYSTEM_PROMPT = """You are a code and document audit assistant.
Analyze the given input and respond ONLY with a valid JSON object - no markdown fences,
no preamble, no explanation outside the JSON.

Schema:
{
  "summary": "A 2-sentence overview of the input.",
  "issues_identified": [
    {
      "type": "Bug | Security Risk | Performance | Style | Other",
      "description": "Clear description of the issue.",
      "severity": "Low | Medium | High"
    }
  ],
  "recommended_fixes": "Actionable advice for optimization, as a single string or short list."
}
"""

def _extract_json(raw_text: str) -> dict:
    text = raw_text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in model response.")
    candidate = text[start:end + 1]
    return json.loads(candidate)


def audit_input(content: str, max_retries: int = 3) -> Optional[dict]:
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            response = client.chat.completions.create(
                model="openai/gpt-oss-120b",
                max_tokens=1500,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": f"Analyze the following input:\n\n{content}"}
                ],
            )

            raw_text = response.choices[0].message.content

            result = _extract_json(raw_text)

            required_keys = {"summary", "issues_identified", "recommended_fixes"}
            if not required_keys.issubset(result.keys()):
                raise ValueError(f"Missing required keys. Got: {list(result.keys())}")

            if not isinstance(result["issues_identified"], list):
                raise ValueError("issues_identified must be a list.")

            return result

        except (groq.APIConnectionError, groq.RateLimitError, groq.APIStatusError) as e:
            last_error = e
            wait = 2 ** attempt
            logger.warning(f"API error on attempt {attempt}/{max_retries}: {e}. Retrying in {wait}s...")
            time.sleep(wait)

        except (json.JSONDecodeError, ValueError) as e:
            last_error = e
            logger.warning(f"Malformed JSON on attempt {attempt}/{max_retries}: {e}. Retrying...")
            time.sleep(1)

    logger.error(f"Audit failed after {max_retries} attempts. Last error: {last_error}")
    return {
        "summary": "Audit failed due to repeated API or parsing errors.",
        "issues_identified": [],
        "recommended_fixes": f"Manual review required. Last error: {str(last_error)}",
        "error": True,
    }


if __name__ == "__main__":
    sample_input = """
    def get_user(id):
        query = "SELECT * FROM users WHERE id = " + id
        return db.execute(query)
    """
    result = audit_input(sample_input)
    print(json.dumps(result, indent=2))
