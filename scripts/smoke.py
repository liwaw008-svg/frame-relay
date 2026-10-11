import json
import re
import time
from pathlib import Path

from genlayer_py import create_account, create_client
from genlayer_py.chains import studionet
from genlayer_py.contracts import actions as contract_actions


def calldata_compat(method=None, args=None, kwargs=None):
    result = {}
    if method is not None:
        result['method'] = method
    if args:
        result['args'] = args
    if kwargs:
        result['kwargs'] = kwargs
    return result


contract_actions.make_calldata_object = calldata_compat
ROOT = Path(__file__).parents[1]
ENV = (ROOT.parents[3] / 'accounts.env').read_text()
DEPLOYMENT = json.loads((ROOT / 'deployment.json').read_text())
ADDRESS = DEPLOYMENT['contractAddress']


def account(number):
    key = re.search(rf'^ACCOUNT_{number}_GENLAYER_PRIVATE_KEY\s*=\s*"?([^"\r\n]+)', ENV, re.M).group(1).strip()
    return create_account(account_private_key=key)


def client(number):
    return create_client(chain=studionet, account=account(number))


def write(number, name, args):
    active = client(number)
    tx = active.write_contract(address=ADDRESS, function_name=name, args=args)
    print(name + '_tx=' + str(tx), flush=True)
    receipt = active.wait_for_transaction_receipt(transaction_hash=tx, wait_until='finalized', retries=180, interval=5000, full_transaction=True)
    leaders = receipt.get('consensus_data', {}).get('leader_receipt') or []
    leaders = [leaders] if isinstance(leaders, dict) else leaders
    assert receipt.get('result_name') == 'MAJORITY_AGREE'
    assert any(item.get('execution_result') == 'SUCCESS' for item in leaders)
    return str(tx)


relay_id = 'RELAY-' + str(int(time.time()))
role_numbers = (1, 3, 5)
creators = [str(account(number).address) for number in role_numbers]
transactions = {}
transactions['open'] = write(4, 'open_relay', [
    relay_id, 'Paper bird launch loop', ['Folded', 'Open', 'Lifted', 'Resting'], creators, 3600,
])
statements = [
    'Begin in the Folded pose and finish in Open over exactly 12 animation ticks.',
    'Begin in the Open pose and finish in Lifted over exactly 18 animation ticks.',
    'Begin in the Lifted pose and finish in Resting over exactly 10 animation ticks.',
]
for number, statement in zip(role_numbers, statements):
    transactions['fragment' + str(number)] = write(number, 'submit_fragment', [relay_id, statement])
transactions['splice'] = write(4, 'splice', [relay_id])
state = client(4).read_contract(address=ADDRESS, function_name='get_relay', args=[relay_id])
assert state['state'] == 'COMPLETE'
assert state['chain_indexes'] == [0, 1, 2]
assert state['total_ticks'] == 40
proof = {'relayId': relay_id, 'transactions': transactions, 'state': state,
         'disclosure': 'The creator wallets are operator-controlled role fixtures, not independent artists.'}
(ROOT / 'evidence').mkdir(exist_ok=True)
(ROOT / 'evidence' / 'live-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
print(json.dumps(proof, indent=2), flush=True)
