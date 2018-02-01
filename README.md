# Toggl to Zoho Invoice connector

![Python 3.6 compatible](https://img.shields.io/badge/python-3.6-green.svg)

Serverless cron job to sync Toggl time entries to Zoho Invoice. It is designed to run as AWS Lambda function triggered by Cloudwatch.

This script syncs the last 7 days (up until yesterday) from Toggl to Zoho invoice.

## Limitations

It uses the Zoho `notes` field to store Toggl record IDs. This will break if you use notes for something else or modify the content of the field.

It will not detect changes in Toggl after the fact and re-sync automatically, but you can delete the record in Zoho completely and it will re-sync it.

Hardcoded timezone "Europe/Berlin" in Zoho.

## Configuration

You need to create a `config.ini` file in the project directory:

```ini
[Toggl]
access_token = _your_toggl_access_token_

[Zoho]
api_key = _your_zoho_api_key_
org_id = _numerical_zoho_organisation_id_
user_id = _numerical_zoho_user_id_

[Mapping]
# Mapping format is Toggl-Project-ID = zoho_project_id:zoho_task_id

# example
123 = 456:789
```

## Installation

```bash
virtualenv -p python3.6 env
pip install -r requirements.txt
serverless deploy
```

to update, use

```bash
serverless deploy function -f cron
```
