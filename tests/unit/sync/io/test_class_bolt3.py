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


import pytest

from neo4j._conf import PoolConfig
from neo4j._sync.io._bolt3 import Bolt3
from neo4j.exceptions import ConfigurationError

from ...._async_compat import mark_sync_test


@pytest.mark.parametrize("set_stale", (True, False))
def test_conn_is_stale(fake_socket, set_stale):
    address = ("127.0.0.1", 7687)
    max_connection_lifetime = 0
    connection = Bolt3(address, fake_socket(address), max_connection_lifetime)
    if set_stale:
        connection.set_stale()
    assert connection.stale() is True


@pytest.mark.parametrize("set_stale", (True, False))
def test_conn_is_not_stale_if_not_enabled(fake_socket, set_stale):
    address = ("127.0.0.1", 7687)
    max_connection_lifetime = -1
    connection = Bolt3(address, fake_socket(address), max_connection_lifetime)
    if set_stale:
        connection.set_stale()
    assert connection.stale() is set_stale


@pytest.mark.parametrize("set_stale", (True, False))
def test_conn_is_not_stale(fake_socket, set_stale):
    address = ("127.0.0.1", 7687)
    max_connection_lifetime = 999999999
    connection = Bolt3(address, fake_socket(address), max_connection_lifetime)
    if set_stale:
        connection.set_stale()
    assert connection.stale() is set_stale


def test_db_extra_not_supported_in_begin(fake_socket):
    address = ("127.0.0.1", 7687)
    connection = Bolt3(address, fake_socket(address), PoolConfig.max_connection_lifetime)
    with pytest.raises(ConfigurationError):
        connection.begin(db="something")


def test_db_extra_not_supported_in_run(fake_socket):
    address = ("127.0.0.1", 7687)
    connection = Bolt3(address, fake_socket(address), PoolConfig.max_connection_lifetime)
    with pytest.raises(ConfigurationError):
        connection.run("", db="something")


@mark_sync_test
def test_simple_discard(fake_socket):
    address = ("127.0.0.1", 7687)
    socket = fake_socket(address, Bolt3.UNPACKER_CLS)
    connection = Bolt3(address, socket, PoolConfig.max_connection_lifetime)
    connection.discard()
    connection.send_all()
    tag, fields = socket.pop_message()
    assert tag == b"\x2F"
    assert len(fields) == 0


@mark_sync_test
def test_simple_pull(fake_socket):
    address = ("127.0.0.1", 7687)
    socket = fake_socket(address, Bolt3.UNPACKER_CLS)
    connection = Bolt3(address, socket, PoolConfig.max_connection_lifetime)
    connection.pull()
    connection.send_all()
    tag, fields = socket.pop_message()
    assert tag == b"\x3F"
    assert len(fields) == 0


@pytest.mark.parametrize("recv_timeout", (1, -1))
@mark_sync_test
def test_hint_recv_timeout_seconds_gets_ignored(
    fake_socket_pair, recv_timeout, mocker
):
    address = ("127.0.0.1", 7687)
    sockets = fake_socket_pair(
        address, Bolt3.PACKER_CLS, Bolt3.UNPACKER_CLS
    )
    sockets.client.settimeout = mocker.Mock()
    sockets.server.send_message(b"\x70", {
        "server": "Neo4j/3.5.0",
        "hints": {"connection.recv_timeout_seconds": recv_timeout},
    })
    connection = Bolt3(
        address, sockets.client, PoolConfig.max_connection_lifetime
    )
    connection.hello()
    sockets.client.settimeout.assert_not_called()
