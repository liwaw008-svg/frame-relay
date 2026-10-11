import base64
import hashlib
import json
from pathlib import Path

from genlayer_py import create_client
from genlayer_py.chains import studionet

ROOT = Path(__file__).parents[1]
deployment = json.loads((ROOT / 'deployment.json').read_text())
tx = create_client(chain=studionet).get_transaction(transaction_hash=deployment['deploymentTransaction'])
deployed = base64.b64decode(tx['data']['contract_code'], validate=True)
local = (ROOT / 'contracts' / 'contract.py').read_text().encode()
leaders = tx.get('consensus_data', {}).get('leader_receipt') or []
leaders = [leaders] if isinstance(leaders, dict) else leaders
output = {
    'contract': deployment['contractAddress'], 'deploymentTransaction': deployment['deploymentTransaction'],
    'status': (tx.get('lifecycle') or {}).get('state', '').upper(), 'consensus': tx.get('result_name'),
    'execution': 'SUCCESS' if any(row.get('execution_result') == 'SUCCESS' for row in leaders) else '',
    'sourceSha256': hashlib.sha256(deployed).hexdigest(), 'sourceMatches': deployed == local,
}
assert output['status'] == 'FINALIZED'
assert output['consensus'] == 'MAJORITY_AGREE'
assert output['execution'] == 'SUCCESS'
assert output['sourceMatches']
(ROOT / 'evidence').mkdir(exist_ok=True)
(ROOT / 'evidence' / 'deployment-verification.json').write_text(json.dumps(output, indent=2) + '\n')
print(json.dumps(output, indent=2))
