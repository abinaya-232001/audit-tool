# Task 3: Cloud Architecture Summary

## Compute & API layer

**API Gateway** is the entry point for the manager-facing app. It handles
request throttling and authentication (via a Cognito authorizer or a simple
API key, depending on the client's existing identity setup) and routes
requests to Lambda. It requires no servers to manage and its pricing tracks
actual usage, which fits a tool that likely sees bursty, unpredictable traffic
rather than constant load - a fixed EC2 instance would mean paying for idle
capacity most of the day.

**Lambda** runs the audit logic from Task 1, split into two functions rather
than one:
- `RequestHandler` - fetches the API key from Secrets Manager, calls the LLM,
  validates the JSON response, and retries on failure.
- `ReportFormatter` - takes the validated result and writes it to storage.

Splitting them means each function's timeout and memory can be tuned to its
actual job (the LLM call needs a longer timeout than a storage write), and a
failed LLM call can be retried without repeating the storage step.

## Storage layer

**S3** stores the full raw JSON report per audit. Reports are write-once,
read-many, and don't need transactional updates, which is exactly what S3 is
built for - and it's inexpensive at this scale.

**DynamoDB** stores lightweight, queryable metadata per report (report ID,
timestamp, submitter, severity counts). This lets the dashboard's "Reports"
list and severity filter respond quickly without pulling every full report
out of S3 just to build a list view.

## Credentials

**AWS Secrets Manager** stores the LLM API key. The `RequestHandler` Lambda's
execution role is granted `secretsmanager:GetSecretValue` scoped to that one
secret's ARN - nothing broader. The key is fetched at invocation time (with
short-lived in-memory caching within a warm container to avoid re-fetching on
every single call) rather than stored in a Lambda environment variable, so
rotating the key doesn't require redeploying the function, and the key is
never visible in the Lambda console, CloudWatch logs, or infrastructure code.

IAM roles follow least privilege throughout: `RequestHandler` gets Secrets
Manager read + CloudWatch write only; `ReportFormatter` gets S3 write +
DynamoDB write only. Neither function can do anything beyond its specific job.

## Cost considerations

Lambda's pay-per-invocation pricing suits this workload well - a tool used by
a handful of managers submitting audits intermittently doesn't justify an
always-on server. S3 and DynamoDB are both usage-based and inexpensive at low
volume. The main variable cost is the LLM API itself, which scales with the
number and size of audits - not with the AWS infrastructure.

## Handling failure

If the LLM call is slow or fails, the goal is for the manager to see a clear
error, not a raw timeout. The `RequestHandler` Lambda's own timeout is set
comfortably above the LLM API's expected response time, and API Gateway's
timeout is set slightly above that - so if something does go wrong, the retry
logic inside Lambda (see Task 1) gets a chance to run before the client ever
sees a generic gateway error. If Secrets Manager itself were unreachable
(rare, but possible), the Lambda would fail fast with a clear internal error
that gets logged to CloudWatch for the engineering team, rather than the
manager receiving a silent, indefinite "Processing..." status.

## Observability

CloudWatch Logs and Alarms watch Lambda error rates and API Gateway 5xx
responses. This matters specifically because the retry logic can mask
transient failures - if a particular error starts happening often enough that
retries are covering for a real, recurring problem, an alarm surfaces that
before it becomes a pattern the team only notices from user complaints.