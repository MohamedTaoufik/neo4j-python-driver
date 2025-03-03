# Copyright (c) "Neo4j"
# Neo4j Sweden AB [https://neo4j.com]
#
# This file is part of Neo4j.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


from socket import (
    AF_INET,
    AF_INET6,
)

import pytest

from neo4j import (
    Address,
    IPv4Address,
)
from neo4j._async_compat.network import NetworkUtil
from neo4j._async_compat.util import Util

from ..._async_compat import mark_sync_test


@mark_sync_test
def test_address_resolve() -> None:
    address = Address(("127.0.0.1", 7687))
    resolved = NetworkUtil.resolve_address(address)
    resolved = Util.list(resolved)
    assert isinstance(resolved, Address) is False
    assert isinstance(resolved, list) is True
    assert len(resolved) == 1
    assert resolved[0] == IPv4Address(('127.0.0.1', 7687))


@mark_sync_test
def test_address_resolve_with_custom_resolver_none() -> None:
    address = Address(("127.0.0.1", 7687))
    resolved = NetworkUtil.resolve_address(address, resolver=None)
    resolved = Util.list(resolved)
    assert isinstance(resolved, Address) is False
    assert isinstance(resolved, list) is True
    assert len(resolved) == 1
    assert resolved[0] == IPv4Address(('127.0.0.1', 7687))


@pytest.mark.parametrize(
    "test_input, expected",
    [
        (Address(("127.0.0.1", "abcd")), ValueError),
        (Address((None, None)), ValueError),
    ]

)
@mark_sync_test
def test_address_resolve_with_unresolvable_address(
    test_input, expected
) -> None:
    with pytest.raises(expected):
        Util.list(
            NetworkUtil.resolve_address(test_input, resolver=None)
        )


@mark_sync_test
@pytest.mark.parametrize("resolver_type", ("sync", "async"))
def test_address_resolve_with_custom_resolver(resolver_type) -> None:
    def custom_resolver_sync(_):
        return [("127.0.0.1", 7687), ("localhost", 1234)]

    def custom_resolver_async(_):
        return [("127.0.0.1", 7687), ("localhost", 1234)]

    if resolver_type == "sync":
        custom_resolver = custom_resolver_sync
    else:
        custom_resolver = custom_resolver_async

    address = Address(("127.0.0.1", 7687))
    resolved = NetworkUtil.resolve_address(
        address, family=AF_INET, resolver=custom_resolver
    )
    resolved = Util.list(resolved)
    assert isinstance(resolved, Address) is False
    assert isinstance(resolved, list) is True
    assert len(resolved) == 2  # IPv4 only
    assert resolved[0] == IPv4Address(('127.0.0.1', 7687))
    assert resolved[1] == IPv4Address(('127.0.0.1', 1234))


@mark_sync_test
def test_address_unresolve() -> None:
    def custom_resolver(_):
        return custom_resolved

    custom_resolved = [("127.0.0.1", 7687), ("localhost", 4321)]

    address = Address(("foobar", 1234))
    unresolved = address._unresolved
    assert address.__class__ == unresolved.__class__
    assert address == unresolved
    resolved = NetworkUtil.resolve_address(
        address, family=AF_INET, resolver=custom_resolver
    )
    resolved_list = Util.list(resolved)
    custom_resolved_addresses = sorted(Address(a) for a in custom_resolved)
    unresolved_list = sorted(a._unresolved for a in resolved_list)
    assert custom_resolved_addresses == unresolved_list
    assert (list(map(lambda a: a.__class__, custom_resolved_addresses))
            == list(map(lambda a: a.__class__, unresolved_list)))
