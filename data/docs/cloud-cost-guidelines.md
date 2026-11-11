# Cloud Cost Guidelines

## Tagging

Every cloud resource (Azure, AWS or GCP) must have the tags `project`, `owner` and `environment`.
Resources without these tags are reported weekly and may be deleted after 14 days.

## Development environments

Development and test environments must be shut down outside working hours (20:00–07:00 and weekends)
using the scheduled automation in the `infra-scheduler` repository.
Use the smallest instance size that works; GPU instances in dev require approval from the Cloud Center of Excellence (CCoE).

## Budgets and alerts

Each project has a monthly cloud budget agreed with the client. Budget alerts are configured at 50%, 80% and 100%.
When the 80% alert fires, the project's tech lead must review spending within 2 working days.

## Data platforms

For Databricks, use job clusters for scheduled pipelines instead of all-purpose clusters,
and set auto-termination to 30 minutes for interactive clusters.
For Snowflake, warehouses must auto-suspend after 5 minutes of inactivity.

## LLM and AI services

Calls to LLM APIs (Claude, Azure OpenAI and others) must go through the internal AI gateway,
which logs usage per project. Each project has a default limit of 500 USD per month for LLM usage;
higher limits are approved by the CCoE.
