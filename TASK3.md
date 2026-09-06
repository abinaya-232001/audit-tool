# Task 3: Cloud Architecture Summary

## Services and rationale

**API Gateway** is the entry point for the app. It handles authentication
(via a Cognito authorizer or API key) and request throttling, then routes to
Lambda. It requires no server management and its cost tracks actual usage -
a good fit since this tool likely sees bursty, unpredictable traffic rather
than constant load.

**Lambda** runs the audit logic, split into two functions:
- `RequestHandler` - fetches the API key from Secrets Manager, calls the
  LLM, validates the JSON response, and retries on failure.
- `ReportFormatter` - converts the validated result into the final report
  and writes it to storage.

Splitting them lets each function's timeout/memory be tuned to its own job,
and lets a failed LLM call be retried without repeating the storage step.

**S3** stores the full raw JSON report per audit - a good fit since reports
are write-once, read-many, and don't need transactional updates.

**DynamoDB** stores lightweight, queryable metadata (report ID, timestamp,
submitter, severity counts), so the dashboard's report list and severity
filter stay fast without pulling every full report out of S3.

## Credential security

The LLM API key lives in **AWS Secrets Manager**, not in code or environment
variables. The `RequestHandler` Lambda's execution role is granted
`secretsmanager:GetSecretValue` scoped to that one secret's ARN only. The
key is fetched at invocation time (with short-lived in-memory caching in a
warm container) rather than stored as an env var, so rotating it doesn't
require redeploying the function, and it's never visible in the Lambda
console or CloudWatch logs.

IAM roles follow least privilege throughout: `RequestHandler` gets Secrets
Manager read + CloudWatch write only; `ReportFormatter` gets S3 write +
DynamoDB write only.

## Cost and failure handling

Lambda's pay-per-invocation pricing suits a tool with intermittent,
low-volume usage better than an always-on server; S3 and DynamoDB are both
usage-based and cheap at this scale. The main variable cost is the LLM API
itself, not the AWS infrastructure.

If the LLM call is slow, Lambda's own timeout is set above the LLM's
expected response time, and API Gateway's timeout is set slightly higher
still - so the retry logic inside Lambda gets a chance to run before the
manager ever sees a raw gateway error. CloudWatch Alarms on Lambda error
rates and API Gateway 5xx responses catch cases where retries are quietly
covering for a real, recurring problem.