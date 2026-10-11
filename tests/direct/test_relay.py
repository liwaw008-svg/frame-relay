from conftest import CONTRACT
import json


POSES = ['Folded', 'Open', 'Lifted', 'Resting']
TEXTS = [
    'Begin Folded and finish Open over exactly 12 animation ticks.',
    'Begin Open and finish Lifted over exactly 18 animation ticks.',
    'Begin Lifted and finish Resting over exactly 10 animation ticks.',
]


def opened(vm, deploy, accounts, window=600, count=3):
    vm.strict_mocks = True; vm.check_pickling = True; vm.warp('2035-01-01T00:00:00+00:00'); vm.sender = accounts[0]
    contract = deploy(CONTRACT)
    contract.open_relay('relay-9', 'Paper bird launch loop', POSES, ['0x' + a.hex() for a in accounts[1:count + 1]], window)
    return contract


def submit(vm, contract, accounts, indexes=(1, 2, 3)):
    for account_index, text in zip(indexes, TEXTS):
        vm.sender = accounts[account_index]; contract.submit_fragment('relay-9', text)


def llm(vm, rows=None):
    rows = rows or [(0, 1, 12), (1, 2, 18), (2, 3, 10)]
    vm.mock_llm(r'.*FrameRelay fragment normalization.*', json.dumps({'rows': [
        {'index': i, 'entry_pose': entry, 'exit_pose': exit_, 'duration_ticks': ticks}
        for i, (entry, exit_, ticks) in enumerate(rows)
    ]}))


def test_complete_chain(direct_vm, direct_deploy, direct_accounts):
    contract = opened(direct_vm, direct_deploy, direct_accounts); submit(direct_vm, contract, direct_accounts); llm(direct_vm)
    contract.splice('relay-9'); row = contract.get_relay('relay-9')
    assert row['state'] == 'COMPLETE' and row['chain_indexes'] == [0, 1, 2] and row['total_ticks'] == 40


def test_longest_partial_chain(direct_vm, direct_deploy, direct_accounts):
    contract = opened(direct_vm, direct_deploy, direct_accounts); submit(direct_vm, contract, direct_accounts)
    llm(direct_vm, [(0, 1, 12), (1, 2, 18), (3, 3, 10)]); contract.splice('relay-9')
    row = contract.get_relay('relay-9'); assert row['state'] == 'PARTIAL' and row['chain_indexes'] == [0, 1]


def test_out_of_order_fragments_are_reordered(direct_vm, direct_deploy, direct_accounts):
    contract = opened(direct_vm, direct_deploy, direct_accounts); submit(direct_vm, contract, direct_accounts)
    llm(direct_vm, [(1, 2, 18), (2, 3, 10), (0, 1, 12)]); contract.splice('relay-9')
    assert contract.get_relay('relay-9')['chain_indexes'] == [2, 0, 1]


def test_named_creator_and_replay(direct_vm, direct_deploy, direct_accounts):
    contract = opened(direct_vm, direct_deploy, direct_accounts); direct_vm.sender = direct_accounts[4]
    with direct_vm.expect_revert('named creator'):
        contract.submit_fragment('relay-9', TEXTS[0])
    direct_vm.sender = direct_accounts[1]; contract.submit_fragment('relay-9', TEXTS[0])
    with direct_vm.expect_revert('one fragment'):
        contract.submit_fragment('relay-9', TEXTS[0])


def test_sparse_expired_round_uses_dense_indexes(direct_vm, direct_deploy, direct_accounts):
    contract = opened(direct_vm, direct_deploy, direct_accounts, 30, 4); submit(direct_vm, contract, direct_accounts, (1, 3, 4))
    direct_vm.warp('2035-01-01T00:00:31+00:00'); llm(direct_vm); contract.splice('relay-9')
    assert contract.get_relay('relay-9')['state'] == 'COMPLETE'


def test_validator_rejects_forged_pose(direct_vm, direct_deploy, direct_accounts):
    contract = opened(direct_vm, direct_deploy, direct_accounts); submit(direct_vm, contract, direct_accounts); llm(direct_vm)
    texts = [{'index': i, 'creator_index': i, 'text': TEXTS[i]} for i in range(3)]
    result = contract._normalize(contract.relays['RELAY-9'], texts); assert direct_vm.run_validator(leader_result=result) is True
    forged = {'rows': [dict(item) for item in result['rows']]}; forged['rows'][0]['exit_pose'] = 3
    assert direct_vm.run_validator(leader_result=forged) is False


def test_permissionless_incomplete_close(direct_vm, direct_deploy, direct_accounts):
    contract = opened(direct_vm, direct_deploy, direct_accounts, 30); direct_vm.warp('2035-01-01T00:00:31+00:00'); direct_vm.sender = direct_accounts[5]
    contract.close_incomplete('relay-9'); assert contract.get_relay('relay-9')['state'] == 'INCOMPLETE'
