"""Server-console administration only. No credential values accepted or printed."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'backend'))
from app import operator_access as operator
from app.provider_transfer import TransferError

p=argparse.ArgumentParser(description='Use the configured server process environment; does not parse .env or print secrets.')
p.add_argument('action',choices=['status','revoke-local'])
p.add_argument('provider',choices=['usgs','cdse','nasa'])
args=p.parse_args()
try:
    if args.action=='revoke-local':
        operator.store().revoke(args.provider)
        print(json.dumps({'locally_revoked':True,'provider_revocation':'not_performed; revoke at issuer separately'}))
    else:print(json.dumps(operator.admin_status(args.provider),ensure_ascii=False))
except TransferError as e:
    print(json.dumps({'state':e.code}));sys.exit(1)
