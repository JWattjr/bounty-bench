"""Shared direct-mode helpers, including Windows-safe gltest cleanup."""

import os
import tempfile

from gltest.direct import loader
from gltest.direct.vm import VMContext


def _windows_safe_message_injection(vm):
    try:
        from genlayer.py import calldata
        from genlayer.py.types import Address
    except ImportError:
        return
    sender_address = Address(vm.sender) if isinstance(vm.sender, bytes) else vm.sender
    contract_address = Address(vm._contract_address) if isinstance(vm._contract_address, bytes) else vm._contract_address
    origin_address = Address(vm.origin) if isinstance(vm.origin, bytes) else vm.origin
    message_data = {
        "contract_address": contract_address,
        "sender_address": sender_address,
        "origin_address": origin_address,
        "stack": [],
        "value": vm._value,
        "datetime": vm._datetime,
        "is_init": False,
        "chain_id": vm._chain_id,
        "entry_kind": 0,
        "entry_data": b"",
        "entry_stage_data": None,
    }
    fd, path = tempfile.mkstemp()
    try:
        os.write(fd, calldata.encode(message_data))
        os.lseek(fd, 0, os.SEEK_SET)
        vm._original_stdin_fd = os.dup(0)
        os.dup2(fd, 0)
        paths = getattr(vm, "_bounty_bench_temp_paths", [])
        paths.append(path)
        vm._bounty_bench_temp_paths = paths
    finally:
        os.close(fd)


_original_cleanup = VMContext._cleanup_after_deactivate


def _cleanup_with_deferred_temp_files(vm):
    _original_cleanup(vm)
    for path in getattr(vm, "_bounty_bench_temp_paths", []):
        try:
            os.unlink(path)
        except FileNotFoundError:
            pass
    vm._bounty_bench_temp_paths = []


loader._inject_message_to_fd0 = _windows_safe_message_injection
VMContext._cleanup_after_deactivate = _cleanup_with_deferred_temp_files


def address_bytes(address):
    return bytes.fromhex(address.removeprefix("0x"))


def selfcall(vm, method, *args):
    previous = vm.sender
    vm.sender = vm._contract_address
    try:
        method(*args)
    finally:
        vm.sender = previous
