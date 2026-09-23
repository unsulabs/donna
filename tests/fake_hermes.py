#!/usr/bin/env python3
"""TEST DOUBLE ONLY. Implements documented CLI shapes, not Hermes or an LLM."""
import json
import os
import sqlite3
import sys
import time

args = sys.argv[1:]
mode = os.environ.get('FAKE_HERMES_MODE', '')
if mode == 'sleep':
    time.sleep(10)
if mode == 'secret-error':
    print('TEST_SECRET_NEVER_LOG_THIS', file=sys.stderr)
    sys.exit(8)
if mode == 'malformed':
    print('not JSON')
    sys.exit(0)
if mode == 'oversized':
    print('x' * 2_000_001)
    sys.exit(0)
if '--help' in args:
    print('--idempotency-key --json --max-runtime --max-retries --parent --skill --script')
    sys.exit(0)
if '--version' in args:
    print('FAKE-HERMES-CONTRACT-FIXTURE 0.0.0')
    sys.exit(0)
if '-p' not in args or os.environ.get('HERMES_HOME') != os.environ.get('FAKE_EXPECT_HOME'):
    print('missing explicit profile identity', file=sys.stderr)
    sys.exit(9)
profile = args[args.index('-p') + 1]
if profile != 'donna':
    sys.exit(9)
if 'kanban' not in args:
    sys.exit(9)
i = args.index('kanban') + 1
if args[i] != '--board':
    sys.exit(9)
i += 2
command, tail = args[i], args[i + 1:]
if command == 'assignees':
    print(json.dumps({'assignees': [{'profile': 'builder'}, {'profile': 'donna'}]}))
    sys.exit(0)
if command == 'diagnostics':
    print(json.dumps({'fixture_only': True, 'dispatcher_running': False}))
    sys.exit(0)
db = sqlite3.connect(os.environ['FAKE_HERMES_DB'], timeout=10)
db.execute('CREATE TABLE IF NOT EXISTS cards (id TEXT PRIMARY KEY, request_key TEXT UNIQUE, data TEXT)')
db.execute('CREATE TABLE IF NOT EXISTS flags (id TEXT PRIMARY KEY)')
def option(name):
    return tail[tail.index(name) + 1]
if command == 'create':
    with db:
        db.execute('BEGIN IMMEDIATE')
        key = option('--idempotency-key')
        row = db.execute('SELECT id FROM cards WHERE request_key=?', (key,)).fetchone()
        if row:
            identifier = row[0]
        else:
            identifier = 't_' + str(db.execute('SELECT count(*) FROM cards').fetchone()[0] + 1)
            data = {'id': identifier, 'status': 'ready', 'tenant': option('--tenant'), 'assignee': option('--assignee'),
                    'result': None, 'updated_at': 'fixture-1', 'run_id': None, 'last_failure_error': False,
                    'title': tail[0], 'body': option('--body')}
            db.execute('INSERT INTO cards VALUES(?,?,?)', (identifier, key, json.dumps(data)))
    if mode == 'lost-response' and not db.execute("SELECT 1 FROM flags WHERE id='lost'").fetchone():
        with db:
            db.execute("INSERT INTO flags VALUES('lost')")
        sys.exit(7)
    print(json.dumps({'task_id': identifier, 'fixture_only': True}))
elif command == 'show':
    row = db.execute('SELECT data FROM cards WHERE id=?', (tail[0],)).fetchone()
    if not row:
        sys.exit(4)
    value = json.loads(row[0])
    if mode == 'unknown-status':
        value['status'] = 'apparently-perfect'
    if mode == 'wrong-id':
        value['id'] = 't_wrong'
    print(json.dumps({'task': value}))
else:
    sys.exit(4)
