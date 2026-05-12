# AI Job Outreach Automation

Python 3.13 outreach system for generating highly personalized recruiting emails with OpenAI and optionally sending them through Gmail SMTP.

Dry-run is the default. Emails are not sent unless `--send` is passed.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

### Google SMTP 
To use Gmail SMTP with this project, you need a **Gmail App Password**, not your normal Gmail password.

Google’s official guidance: App Passwords are 16-digit passcodes for apps/devices, and they require 2-Step Verification to be enabled. Source: https://support.google.com/mail/answer/185833

**Steps**

1. Enable 2-Step Verification on your Google account:
   https://myaccount.google.com/security

2. Create an App Password:
   https://myaccount.google.com/apppasswords

3. Name it something like `cv-thingi SMTP`.

4. Copy the 16-character password Google shows you.

5. Create your real `.env` file from `.env.example`:

```powershell
Copy-Item .env.example .env
```

6. Fill in these values in `.env`:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=465
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-16-character-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_FROM_NAME=Your Name
```

For this codebase, use port `465` because [outreach/email/sender.py](</c:/Users/dell/Documents/cv-thingi/outreach/email/sender.py>) uses `smtplib.SMTP_SSL`.

Then run a dry-run first:

```powershell
.\.venv\Scripts\Activate.ps1
python main.py --contacts data/contacts.csv --resume data/resume.pdf
```

To actually send:

```powershell
python main.py --contacts data/contacts.csv --resume data/resume.pdf --send --limit 1
```

Start with `--limit 1` so you can verify the first real email safely.

Edit `.env` with your OpenAI key and Gmail App Password.

## Contacts CSV

Required column: `Email`

Optional columns:

```csv
Email,Company Name,Tone,Contact Name,Role,Job URL,Website URL,Notes
recruiting@example.com,Example Co,Technical,Alex,Backend Engineer,https://example.com/jobs/backend,https://example.com,"Interested in Python automation"
```

## Run

Generate drafts only:

```powershell
python main.py --contacts data/contacts.csv --resume data/resume.pdf --portfolio data/profile.md
```

Send, still capped by limits:

```powershell
python main.py --contacts data/contacts.csv --resume data/resume.pdf --send --limit 10
```

Outputs are written to `outputs/`. Logs are written to `logs/outreach.log`.

## Safety Notes

- Use a Gmail App Password, not your normal Gmail password.
- Keep `.env` private.
- Respect site terms, robots.txt, and rate limits.
- Review generated drafts before sending to real companies.
- Automated follow-ups are intentionally not included.
