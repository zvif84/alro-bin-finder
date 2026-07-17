"""
Alro Bin Finder — email inbox checker
Runs inside GitHub Actions on a schedule. Checks a dedicated Gmail inbox for
unread emails from approved senders carrying an .xlsx attachment. If found,
saves the newest one as BINS.xlsx and signals the workflow to rebuild.

Required environment variables (set as GitHub repo Secrets):
  GMAIL_ADDRESS      the dedicated inbox, e.g. alro.bins@gmail.com
  GMAIL_APP_PASSWORD 16-character Google App Password (not the normal password)
  ALLOWED_SENDERS    comma-separated list of approved sender emails
"""
import imaplib
import email
import email.utils
import os
import sys
import datetime


def get_output_path():
    return os.environ.get('GITHUB_OUTPUT', '/dev/null')


def newest_xlsx_from_inbox():
    user = os.environ['GMAIL_ADDRESS']
    pw = os.environ['GMAIL_APP_PASSWORD']
    allowed = [s.strip().lower() for s in os.environ.get('ALLOWED_SENDERS', '').split(',') if s.strip()]
    if not allowed:
        sys.exit('ERROR: ALLOWED_SENDERS is empty. Refusing to accept mail from anyone.')

    box = imaplib.IMAP4_SSL('imap.gmail.com')
    box.login(user, pw)
    box.select('INBOX')

    typ, data = box.search(None, 'UNSEEN')
    ids = data[0].split()
    print(f'Unread emails: {len(ids)}')

    best = None  # (date, filename, bytes)
    for msg_id in ids:
        typ, msg_data = box.fetch(msg_id, '(RFC822)')  # fetching marks it read
        msg = email.message_from_bytes(msg_data[0][1])
        sender = email.utils.parseaddr(msg.get('From', ''))[1].lower()
        if sender not in allowed:
            print(f'Ignoring email from unapproved sender: {sender}')
            continue
        for part in msg.walk():
            name = (part.get_filename() or '').strip()
            if name.lower().endswith('.xlsx'):
                payload = part.get_payload(decode=True)
                if not payload:
                    continue
                try:
                    when = email.utils.parsedate_to_datetime(msg.get('Date'))
                except Exception:
                    when = datetime.datetime.now(datetime.timezone.utc)
                if best is None or when > best[0]:
                    best = (when, name, payload)
                print(f'Found attachment "{name}" from {sender} ({when})')
    box.logout()
    return best


def main():
    best = newest_xlsx_from_inbox()
    if best is None:
        print('No new spreadsheet. Nothing to do.')
        with open(get_output_path(), 'a') as f:
            f.write('updated=false\n')
        return
    when, name, payload = best
    with open('BINS.xlsx', 'wb') as f:
        f.write(payload)
    print(f'Saved "{name}" as BINS.xlsx ({len(payload):,} bytes). Rebuild will follow.')
    with open(get_output_path(), 'a') as f:
        f.write('updated=true\n')


if __name__ == '__main__':
    main()
