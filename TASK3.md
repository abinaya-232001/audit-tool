# Task 3: Cloud Architecture Summary

## Compute & API layer

- **API Gateway** - front door for the manager-facing app; handles request throttling,
  auth (via a Cognito authorizer or API key), and routes to Lambda. No servers to
  manage, scales automatically, and cost tracks usage - appropriate for a tool with
  bursty, non-constant traffic.
- **Lambda** - runs the audit script. Split into two functions: a `RequestHandler`
  (calls the LLM, validates JSON, retries) and a `ReportFormatter` (writes to storage).
  Splitting them keeps each function's timeout and memory tuned to its actual job, and
  lets you retry the LLM call without re-running storage logic.

## Storage layer

- **S3** - stores the full raw JSON report per audit (cheap, durable, versionable).
  Good fit since reports are write-once, read-many, and do not need transactional
  updates.
- **DynamoDB** - stores lightweight metadata (report ID, timestamp, submitter, severity
  counts) so the dashboard can query/filter without pulling every S3 object. Keeps the
  dashboard fast and S3 costs low.

## Credentials

- **AWS Secrets Manager** stores the LLM API key. Lambda's execution role is granted
  `secretsmanager:GetSecretValue` scoped to that one secret's ARN only. The key is
  fetched at invocation (with short-lived in-memory caching per warm container) rather
  than baked into environment variables, so rotation does not require redeploying the
  function, and the key is never visible in the Lambda console or CloudWatch logs.
- IAM roles follow least privilege: the `RequestHandler` role gets Secrets Manager read
  + CloudWatch write only; the `ReportFormatter` role gets S3 write + DynamoDB write
  only. Neither function has permissions it does not use.

## Observability

- CloudWatch Logs/Alarms on Lambda error rates and API Gateway 5xx responses, since
  retry logic can mask transient failures that still deserve visibility if they start
  recurring.
