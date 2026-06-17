# Security Policy

## Supported Version

Security fixes are applied to the latest version on the default branch.

## Reporting a Vulnerability

Do not open a public issue for a suspected vulnerability.

Email [sahir.vhora@gmail.com](mailto:sahir.vhora@gmail.com) with:

- a description of the issue
- steps to reproduce it
- the potential impact
- a suggested mitigation, if available

You should receive an acknowledgement within 48 hours.

## Data Handling

SF Change Ledger is designed to run locally against exported configuration.
Uploaded files are written only to an operating-system temporary directory for
the duration of the comparison. The application does not call SAP
SuccessFactors, send telemetry, or persist uploaded tenant exports.

The development server binds to `127.0.0.1` by default. Do not expose it to a
shared network without adding production authentication, CSRF protection,
durable encrypted storage controls, and an approved WSGI deployment.

## User Responsibilities

- Keep tenant exports outside source control.
- Remove client names and sensitive configuration before sharing examples.
- Do not upload employee data; the tool is intended for configuration only.
- Review generated findings before using them in governance decisions.
