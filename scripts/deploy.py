import hashlib
import json
import re
import subprocess
from pathlib import Path

from genlayer_py import create_account, create_client
from genlayer_py.chains import studionet

ROOT = Path(__file__).parents[1]
ENV = (ROOT.parents[3] / 'accounts.env').read_text()
KEY = re.search(r'^ACCOUNT_4_GENLAYER_PRIVATE_KEY\s*=\s*"?([^"\r\n]+)', ENV, re.M).group(1).strip()
ACCOUNT = create_account(account_private_key=KEY)
CLIENT = create_client(chain=studionet, account=ACCOUNT)
CODE = (ROOT / 'contracts' / 'contract.py').read_text()
COMMIT = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()

tx = CLIENT.deploy_contract(code=CODE, args=[])
print('deploy_tx=' + str(tx), flush=True)
receipt = CLIENT.wait_for_transaction_receipt(transaction_hash=tx, wait_until='finalized', retries=180, interval=5000, full_transaction=True)
leaders = receipt.get('consensus_data', {}).get('leader_receipt') or []
leaders = [leaders] if isinstance(leaders, dict) else leaders
address = receipt.get('data', {}).get('contract_address') or receipt.get('to_address')
assert receipt.get('result_name') == 'MAJORITY_AGREE'
assert any(item.get('execution_result') == 'SUCCESS' for item in leaders)
deployment = {
    'network': 'StudioNet', 'account': 'liwaw008-svg', 'deployerAddress': str(ACCOUNT.address),
    'contractAddress': address, 'deploymentTransaction': str(tx),
    'deploymentConsensus': receipt.get('result_name'), 'deploymentExecution': 'SUCCESS',
    'sourceSha256': hashlib.sha256(CODE.encode()).hexdigest(), 'sourceCommit': COMMIT,
    'repository': 'https://github.com/liwaw008-svg/frame-relay',
}
(ROOT / 'deployment.json').write_text(json.dumps(deployment, indent=2) + '\n')
print(json.dumps(deployment, indent=2), flush=True)
