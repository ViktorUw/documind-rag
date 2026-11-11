# IT Security Guidelines

## Passwords and accounts

Passwords must be at least 14 characters long. We recommend using the company password manager (1Password).
Multi-factor authentication (MFA) is mandatory for all company accounts, including email, GitHub and cloud consoles.
Never share your credentials with anyone, including the IT team. IT will never ask for your password.

## Laptops

All company laptops must have full-disk encryption enabled (BitLocker on Windows, FileVault on macOS, LUKS on Linux).
The screen must lock automatically after 5 minutes of inactivity.
Lost or stolen devices must be reported to security@nimbusdata.example within 1 hour.

## Client data

Client data must never be copied to personal devices or personal cloud storage.
Production client data may not be used in development environments; use the anonymised datasets
from the internal data catalog instead.
Sharing client data with external AI tools is forbidden unless the tool is on the approved list
maintained by the Security team.

## Reporting incidents

Report any suspected phishing email using the "Report phishing" button in Outlook.
For any other security incident, contact the Security team on Slack in #security-incidents
or by email at security@nimbusdata.example. The on-call security engineer responds within 30 minutes.
