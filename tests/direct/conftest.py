import os

_unlink = os.unlink


def safe_unlink(path, *args, **kwargs):
    try:
        return _unlink(path, *args, **kwargs)
    except PermissionError:
        return None


os.unlink = safe_unlink


def _calldata():
    from genlayer.py import calldata
    return calldata


def _types():
    from genlayer.py import types
    return types


def _address():
    return _types().Address


def _address_u256():
    types = _types()
    return types.Address, types.u256


def _lazy():
    return _types().Lazy


def _allocate_contract(contract_cls, vm, *args, **kwargs):
    from genlayer.py.storage import ROOT_SLOT_ID
    from genlayer.py.storage._internal.generate import ORIGINAL_INIT_ATTR, _storage_build
    type_desc = _storage_build(contract_cls, {})
    instance = type_desc.get(vm._storage.get_store_slot(ROOT_SLOT_ID), 0)
    init = getattr(getattr(type_desc, 'cls', contract_cls), '__init__', None)
    if init is not None:
        if hasattr(init, ORIGINAL_INIT_ATTR):
            init = getattr(init, ORIGINAL_INIT_ATTR)
        init(instance, *args, **kwargs)
    return instance


def _sync_message_context(**updates):
    import genlayer.gl as gl_module
    normalized = {key: value for key, value in updates.items() if value is not sdk_compat._UNSET}
    message_updates = {key: value for key, value in normalized.items() if key in gl_module.message._fields}
    if message_updates:
        gl_module.message = gl_module.message._replace(**message_updates)
    if isinstance(gl_module.message_raw, dict):
        gl_module.message_raw.update(normalized)


def _refresh_gl_message(vm):
    import sys
    if 'genlayer.gl' not in sys.modules:
        return
    Address, u256 = _address_u256()
    sender = vm.sender
    if sender is not None and not isinstance(sender, Address):
        sender = Address(sender.as_bytes if hasattr(sender, 'as_bytes') else sender)
    origin = vm.origin
    if origin is not None and not isinstance(origin, Address):
        origin = Address(origin.as_bytes if hasattr(origin, 'as_bytes') else origin)
    _sync_message_context(sender_address=sender, origin_address=origin, value=u256(vm._value), chain_id=u256(vm._chain_id))


import gltest.direct.loader as direct_loader
import gltest.direct.sdk_compat as sdk_compat
import gltest.direct.vm as direct_vm_module
import gltest.direct.wasi_mock as wasi_mock

_original_nondet_patch = direct_loader._patch_run_nondet_for_direct_mode


def _patch_nondet_for_direct_mode():
    import sys
    import genlayer.gl.vm as gl_vm
    _original_nondet_patch()

    def direct_unsafe(leader_fn, validator_fn, /, **kwargs):
        vm = wasi_mock.get_vm()
        vm._in_nondet = True
        try:
            result = leader_fn()
        finally:
            vm._in_nondet = False
        vm._captured_validators.append((result, leader_fn, validator_fn))
        return result

    def direct_spawn(fn, *, allow_write_ops=False):
        vm = wasi_mock.get_vm()
        vm._in_nondet = True
        try:
            return gl_vm.Return(calldata=fn())
        except gl_vm.UserError as error:
            return error
        finally:
            vm._in_nondet = False

    direct_unsafe.lazy = lambda leader_fn, validator_fn, **kwargs: _lazy()(lambda: direct_unsafe(leader_fn, validator_fn, **kwargs))
    direct_spawn.lazy = lambda fn, **kwargs: _lazy()(lambda: direct_spawn(fn, **kwargs))
    gl_vm.run_nondet = direct_unsafe
    gl_vm.run_nondet_unsafe = direct_unsafe
    gl_vm.spawn_sandbox = direct_spawn
    sys.modules['genlayer.vm'] = gl_vm


sdk_compat.import_calldata = _calldata
sdk_compat.import_types = _types
sdk_compat.import_address = _address
sdk_compat.import_address_u256 = _address_u256
sdk_compat.import_lazy = _lazy
direct_loader.import_calldata = _calldata
direct_loader.import_address = _address
direct_loader.import_lazy = _lazy
direct_loader._allocate_contract = _allocate_contract
direct_loader._patch_run_nondet_for_direct_mode = _patch_nondet_for_direct_mode
direct_vm_module.import_address_u256 = _address_u256
direct_vm_module.sync_message_context = _sync_message_context
direct_vm_module.VMContext._refresh_gl_message = _refresh_gl_message
wasi_mock.import_calldata = _calldata

CONTRACT = os.path.join('contracts', 'contract.py')

