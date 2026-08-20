"""
Alro Bin Finder — email inbox checker (v2)
Runs inside GitHub Actions on a schedule. Checks a dedicated Gmail inbox for
unread emails from approved senders carrying a .csv or .xlsx attachment. If
found, saves the newest one as BINS.csv or BINS.xlsx (removing the stale
counterpart) and signals the workflow to rebuild.

Required environment variables (set as GitHub repo Secrets):
  GMAIL_ADDRESS      the dedicated inbox, e.g. alro.bin.system@gmail.com
  GMAIL_APP_PASSWORD 16-character Google App Password (not the normal password)
  ALLOWED_SENDERS    comma-separated list of approved sender emails
"""
import imaplib
import email
import email.utils
import os
import sys
import datetime

ACCEPTED_EXTENSIONS = ('.csv', '.xlsx')


def get_output_path():
    return os.environ.get('GITHUB_OUTPUT', '/dev/null')


def newest_data_file_from_inbox():
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
    processed = []  # approved-sender messages get trashed after this poll
    for msg_id in ids:
        typ, msg_data = box.fetch(msg_id, '(RFC822)')  # fetching marks it read
        msg = email.message_from_bytes(msg_data[0][1])
        sender = email.utils.parseaddr(msg.get('From', ''))[1].lower()
        if sender not in allowed:
            print(f'Ignoring email from unapproved sender: {sender}')
            continue
        processed.append(msg_id)
        for part in msg.walk():
            name = (part.get_filename() or '').strip()
            if name.lower().endswith(ACCEPTED_EXTENSIONS):
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
    # Move processed data emails to Trash (Gmail purges Trash after 30 days).
    # At 48 scheduled reports/day this keeps the free inbox from ever filling up.
    for msg_id in processed:
        try:
            box.store(msg_id, '+X-GM-LABELS', '\\Trash')
        except Exception as e:
            print(f'Note: could not trash message {msg_id}: {e}')
    if processed:
        print(f'Moved {len(processed)} processed email(s) to Trash.')
    box.logout()
    return best


def main():
    best = newest_data_file_from_inbox()
    if best is None:
        print('No new data file. Nothing to do.')
        with open(get_output_path(), 'a') as f:
            f.write('updated=false\n')
        return
    when, name, payload = best

    ext = '.csv' if name.lower().endswith('.csv') else '.xlsx'
    target = 'BINS' + ext
    stale = 'BINS.xlsx' if ext == '.csv' else 'BINS.csv'
    with open(target, 'wb') as f:
        f.write(payload)
    if os.path.exists(stale):
        os.remove(stale)
        print(f'Removed stale {stale} (replaced by {target}).')

    print(f'Saved "{name}" as {target} ({len(payload):,} bytes). Rebuild will follow.')
    with open(get_output_path(), 'a') as f:
        f.write('updated=true\n')


if __name__ == '__main__':
    main()
