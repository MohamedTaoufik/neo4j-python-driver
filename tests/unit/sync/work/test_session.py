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


from contextlib import contextmanager

import pytest

from neo4j import (
    Bookmarks,
    ManagedTransaction,
    Session,
    Transaction,
    unit_of_work,
)
from neo4j._conf import SessionConfig
from neo4j._sync.io import (
    BoltPool,
    Neo4jPool,
)
from neo4j.api import BookmarkManager

from ...._async_compat import mark_sync_test


@contextmanager
def assert_warns_tx_func_deprecation(tx_func_name):
    if tx_func_name.endswith("_transaction"):
        mode = tx_func_name.split("_")[0]
        with pytest.warns(
            DeprecationWarning,
            match=f"^{mode}_transaction has been renamed to execute_{mode}$"
        ):
            yield
    else:
        yield


@mark_sync_test
def test_session_context_calls_close(mocker):
    s = Session(None, SessionConfig())
    mock_close = mocker.patch.object(s, 'close', autospec=True,
                                     side_effect=s.close)
    with s:
        pass
    mock_close.assert_called_once_with()


@pytest.mark.parametrize("test_run_args", (
    ("RETURN $x", {"x": 1}), ("RETURN 1",)
))
@pytest.mark.parametrize(("repetitions", "consume"), (
    (1, False), (2, False), (2, True)
))
@mark_sync_test
def test_opens_connection_on_run(
    fake_pool, test_run_args, repetitions, consume
):
    with Session(fake_pool, SessionConfig()) as session:
        assert session._connection is None
        result = session.run(*test_run_args)
        assert session._connection is not None
        if consume:
            result.consume()


@pytest.mark.parametrize("test_run_args", (
    ("RETURN $x", {"x": 1}), ("RETURN 1",)
))
@pytest.mark.parametrize("repetitions", range(1, 3))
@mark_sync_test
def test_closes_connection_after_consume(
    fake_pool, test_run_args, repetitions
):
    with Session(fake_pool, SessionConfig()) as session:
        result = session.run(*test_run_args)
        result.consume()
        assert session._connection is None
    assert session._connection is None


@pytest.mark.parametrize("test_run_args", (
    ("RETURN $x", {"x": 1}), ("RETURN 1",)
))
@mark_sync_test
def test_keeps_connection_until_last_result_consumed(
    fake_pool, test_run_args
):
    with Session(fake_pool, SessionConfig()) as session:
        result1 = session.run(*test_run_args)
        result2 = session.run(*test_run_args)
        assert session._connection is not None
        result1.consume()
        assert session._connection is not None
        result2.consume()
        assert session._connection is None


@mark_sync_test
def test_opens_connection_on_tx_begin(fake_pool):
    with Session(fake_pool, SessionConfig()) as session:
        assert session._connection is None
        with session.begin_transaction() as _:
            assert session._connection is not None


@pytest.mark.parametrize("test_run_args", (
    ("RETURN $x", {"x": 1}), ("RETURN 1",)
))
@pytest.mark.parametrize("repetitions", range(1, 3))
@mark_sync_test
def test_keeps_connection_on_tx_run(
    fake_pool, test_run_args, repetitions
):
    with Session(fake_pool, SessionConfig()) as session:
        with session.begin_transaction() as tx:
            for _ in range(repetitions):
                tx.run(*test_run_args)
                assert session._connection is not None


@pytest.mark.parametrize("test_run_args", (
        ("RETURN $x", {"x": 1}), ("RETURN 1",)
))
@pytest.mark.parametrize("repetitions", range(1, 3))
@mark_sync_test
def test_keeps_connection_on_tx_consume(
    fake_pool, test_run_args, repetitions
):
    with Session(fake_pool, SessionConfig()) as session:
        with session.begin_transaction() as tx:
            for _ in range(repetitions):
                result = tx.run(*test_run_args)
                result.consume()
                assert session._connection is not None


@pytest.mark.parametrize("test_run_args", (
        ("RETURN $x", {"x": 1}), ("RETURN 1",)
))
@mark_sync_test
def test_closes_connection_after_tx_close(fake_pool, test_run_args):
    with Session(fake_pool, SessionConfig()) as session:
        with session.begin_transaction() as tx:
            for _ in range(2):
                result = tx.run(*test_run_args)
                result.consume()
            tx.close()
            assert session._connection is None
        assert session._connection is None


@pytest.mark.parametrize("test_run_args", (
        ("RETURN $x", {"x": 1}), ("RETURN 1",)
))
@mark_sync_test
def test_closes_connection_after_tx_commit(fake_pool, test_run_args):
    with Session(fake_pool, SessionConfig()) as session:
        with session.begin_transaction() as tx:
            for _ in range(2):
                result = tx.run(*test_run_args)
                result.consume()
            tx.commit()
            assert session._connection is None
        assert session._connection is None


@pytest.mark.parametrize(
    "bookmark_values",
    (None, [], ["abc"], ["foo", "bar"], {"a", "b"}, ("1", "two"))
)
@mark_sync_test
def test_session_returns_bookmarks_directly(fake_pool, bookmark_values):
    if bookmark_values is not None:
        bookmarks = Bookmarks.from_raw_values(bookmark_values)
    else:
        bookmarks = Bookmarks()
    with Session(
        fake_pool, SessionConfig(bookmarks=bookmarks)
    ) as session:
        ret_bookmarks = (session.last_bookmarks())
        assert isinstance(ret_bookmarks, Bookmarks)
        ret_bookmarks = ret_bookmarks.raw_values
        if bookmark_values is None:
            assert ret_bookmarks == frozenset()
        else:
            assert ret_bookmarks == frozenset(bookmark_values)


@pytest.mark.parametrize(
    "bookmarks",
    (None, [], ["abc"], ["foo", "bar"], ("1", "two"))
)
@mark_sync_test
def test_session_last_bookmark_is_deprecated(fake_pool, bookmarks):
    if bookmarks is not None:
        with pytest.warns(DeprecationWarning):
            session = Session(fake_pool,
                                   SessionConfig(bookmarks=bookmarks))
    else:
        session = Session(fake_pool, SessionConfig(bookmarks=bookmarks))
    with session:
        with pytest.warns(DeprecationWarning):
            if bookmarks:
                assert (session.last_bookmark()) == bookmarks[-1]
            else:
                assert (session.last_bookmark()) is None


@pytest.mark.parametrize(
    "bookmarks",
    (("foo",), ("foo", "bar"), (), ["foo", "bar"], {"a", "b"})
)
@mark_sync_test
def test_session_bookmarks_as_iterable_is_deprecated(
    fake_pool, bookmarks
):
    with pytest.warns(DeprecationWarning):
        with Session(fake_pool, SessionConfig(
            bookmarks=bookmarks
        )) as session:
            ret_bookmarks = (session.last_bookmarks()).raw_values
            assert ret_bookmarks == frozenset(bookmarks)


@pytest.mark.parametrize(("query", "error_type"), (
    (None, ValueError),
    (1234, TypeError),
    ({"how about": "no?"}, TypeError),
    (["I don't", "think so"], TypeError),
))
@mark_sync_test
def test_session_run_wrong_types(fake_pool, query, error_type):
    with Session(fake_pool, SessionConfig()) as session:
        with pytest.raises(error_type):
            session.run(query)


@pytest.mark.parametrize("tx_type", ("write_transaction", "read_transaction",
                                     "execute_write", "execute_read",))
@mark_sync_test
def test_tx_function_argument_type(fake_pool, tx_type):
    called = False

    def work(tx):
        nonlocal called
        called = True
        assert isinstance(tx, ManagedTransaction)

    with Session(fake_pool, SessionConfig()) as session:
        with assert_warns_tx_func_deprecation(tx_type):
            getattr(session, tx_type)(work)
        assert called


@pytest.mark.parametrize("tx_type", ("write_transaction", "read_transaction",
                                     "execute_write", "execute_read"))
@pytest.mark.parametrize("decorator_kwargs", (
    {},
    {"timeout": 5},
    {"metadata": {"foo": "bar"}},
    {"timeout": 5, "metadata": {"foo": "bar"}},

))
@mark_sync_test
def test_decorated_tx_function_argument_type(
    fake_pool, tx_type, decorator_kwargs
):
    called = False

    @unit_of_work(**decorator_kwargs)
    def work(tx):
        nonlocal called
        called = True
        assert isinstance(tx, ManagedTransaction)

    with Session(fake_pool, SessionConfig()) as session:
        with assert_warns_tx_func_deprecation(tx_type):
            getattr(session, tx_type)(work)
        assert called
    assert len(fake_pool.acquired_connection_mocks) == 1
    cx = fake_pool.acquired_connection_mocks[0]
    cx.begin.assert_called_once()
    for key in ("timeout", "metadata"):
        value = decorator_kwargs.get(key)
        assert cx.begin.call_args[1][key] == value


@mark_sync_test
def test_session_tx_type(fake_pool):
    with Session(fake_pool, SessionConfig()) as session:
        tx = session.begin_transaction()
        assert isinstance(tx, Transaction)


@pytest.mark.parametrize("parameters", (
    {"x": None},
    {"x": True},
    {"x": False},
    {"x": 123456789},
    {"x": 3.1415926},
    {"x": float("nan")},
    {"x": float("inf")},
    {"x": float("-inf")},
    {"x": "foo"},
    {"x": bytearray([0x00, 0x33, 0x66, 0x99, 0xCC, 0xFF])},
    {"x": b"\x00\x33\x66\x99\xcc\xff"},
    {"x": [1, 2, 3]},
    {"x": ["a", "b", "c"]},
    {"x": ["a", 2, 1.234]},
    {"x": ["a", 2, ["c"]]},
    {"x": {"one": "eins", "two": "zwei", "three": "drei"}},
    {"x": {"one": ["eins", "uno", 1], "two": ["zwei", "dos", 2]}},
))
@pytest.mark.parametrize("run_type", ("auto", "unmanaged", "managed"))
@mark_sync_test
def test_session_run_with_parameters(fake_pool, parameters, run_type):
    with Session(fake_pool, SessionConfig()) as session:
        if run_type == "auto":
            session.run("RETURN $x", **parameters)
        elif run_type == "unmanaged":
            tx = session.begin_transaction()
            tx.run("RETURN $x", **parameters)
        elif run_type == "managed":
            def work(tx):
                tx.run("RETURN $x", **parameters)
            session.execute_write(work)
        else:
            raise ValueError(run_type)

    assert len(fake_pool.acquired_connection_mocks) == 1
    connection_mock = fake_pool.acquired_connection_mocks[0]
    connection_mock.run.assert_called_once()
    call = connection_mock.run.call_args
    assert call.args[0] == "RETURN $x"
    assert call.kwargs["parameters"] == parameters


@pytest.mark.parametrize(
    ("params", "kw_params", "expected_params"),
    (
        ({"x": 1}, {}, {"x": 1}),
        ({}, {"x": 1}, {"x": 1}),
        ({"x": 1}, {"y": 2}, {"x": 1, "y": 2}),
        ({"x": 1}, {"x": 2}, {"x": 2}),
        ({"x": 1}, {"x": 2}, {"x": 2}),
        ({"x": 1, "y": 3}, {"x": 2}, {"x": 2, "y": 3}),
        ({"x": 1}, {"x": 2, "y": 3}, {"x": 2, "y": 3}),
        # potentially internally used keyword arguments
        ({}, {"timeout": 2}, {"timeout": 2}),
        ({"timeout": 2}, {}, {"timeout": 2}),
        ({}, {"imp_user": "hans"}, {"imp_user": "hans"}),
        ({"imp_user": "hans"}, {}, {"imp_user": "hans"}),
        ({}, {"db": "neo4j"}, {"db": "neo4j"}),
        ({"db": "neo4j"}, {}, {"db": "neo4j"}),
        ({}, {"database": "neo4j"}, {"database": "neo4j"}),
        ({"database": "neo4j"}, {}, {"database": "neo4j"}),
    )
)
@pytest.mark.parametrize("run_type", ("auto", "unmanaged", "managed"))
@mark_sync_test
def test_session_run_parameter_precedence(
    fake_pool, params, kw_params, expected_params, run_type
):
    with Session(fake_pool, SessionConfig()) as session:
        if run_type == "auto":
            session.run("RETURN $x", params, **kw_params)
        elif run_type == "unmanaged":
            tx = session.begin_transaction()
            tx.run("RETURN $x", params, **kw_params)
        elif run_type == "managed":
            def work(tx):
                tx.run("RETURN $x", params, **kw_params)
            session.execute_write(work)
        else:
            raise ValueError(run_type)

    assert len(fake_pool.acquired_connection_mocks) == 1
    connection_mock = fake_pool.acquired_connection_mocks[0]
    connection_mock.run.assert_called_once()
    call = connection_mock.run.call_args
    assert call.args[0] == "RETURN $x"
    assert call.kwargs["parameters"] == expected_params


@pytest.mark.parametrize("db", (None, "adb"))
@pytest.mark.parametrize("routing", (True, False))
# no home db resolution when connected to Neo4j 4.3 or earlier
@pytest.mark.parametrize("home_db_gets_resolved", (True, False))
@pytest.mark.parametrize("additional_session_bookmarks",
                         (None, ["session", "bookmarks"]))
@mark_sync_test
def test_with_bookmark_manager(
    fake_pool, db, routing, scripted_connection, home_db_gets_resolved,
    additional_session_bookmarks, mocker
):
    def update_routing_table_side_effect(
        database, imp_user, bookmarks, acquisition_timeout=None,
        database_callback=None
    ):
        if home_db_gets_resolved:
            database_callback("homedb")

    def bmm_get_bookmarks():
        nonlocal get_bookmarks_count
        get_bookmarks_count += 1
        return ["all", f"bookmarks{get_bookmarks_count}"]

    get_bookmarks_count = 0

    scripted_connection.set_script([
        ("run", {"on_success": None, "on_summary": None}),
        ("pull", {
            "on_success": ({"bookmark": "res:bm1", "has_more": False},),
            "on_summary": None,
            "on_records": None,
        })
    ])
    fake_pool.buffered_connection_mocks.append(scripted_connection)

    bmm = mocker.Mock(spec=BookmarkManager)
    bmm.get_bookmarks.side_effect = bmm_get_bookmarks

    if routing:
        fake_pool.mock_add_spec(Neo4jPool)
        fake_pool.update_routing_table.side_effect = \
            update_routing_table_side_effect
    else:
        fake_pool.mock_add_spec(BoltPool)

    config = SessionConfig()
    config.bookmark_manager = bmm
    if db is not None:
        config.database = db
    if additional_session_bookmarks:
        config.bookmarks = Bookmarks.from_raw_values(
            additional_session_bookmarks
        )
    with Session(fake_pool, config) as session:
        assert not bmm.method_calls

        session.run("RETURN 1")

        # assert called bmm accordingly
        expected_bmm_method_calls = [mocker.call.get_bookmarks(),
                                     mocker.call.get_bookmarks()]
        if routing and db is None:
            expected_bmm_method_calls = [
                # extra call for resolving the home database
                mocker.call.get_bookmarks(),
                *expected_bmm_method_calls
            ]
        assert bmm.method_calls == expected_bmm_method_calls
        assert bmm.get_bookmarks.call_count == len(expected_bmm_method_calls)
        bmm.method_calls.clear()

    expected_bookmarks_home_db_resolution = {
        "all", "bookmarks1", *(additional_session_bookmarks or [])
    }
    expected_bookmarks_acquire = {
        "all", f"bookmarks{len(expected_bmm_method_calls) - 1}",
        *(additional_session_bookmarks or [])
    }
    expected_bookmarks_run = {
        "all", f"bookmarks{len(expected_bmm_method_calls)}",
        *(additional_session_bookmarks or [])
    }
    assert [call[0] for call in bmm.method_calls] == ["update_bookmarks"]
    assert bmm.method_calls[0].kwargs == {}
    assert len(bmm.method_calls[0].args) == 2
    assert (set(bmm.method_calls[0].args[0])
            == expected_bookmarks_run)
    assert set(bmm.method_calls[0].args[1]) == {"res:bm1"}

    expected_pool_method_calls = ["acquire", "release"]
    if routing and db is None:
        expected_pool_method_calls = ["update_routing_table",
                                      *expected_pool_method_calls]
    assert ([call[0] for call in fake_pool.method_calls]
            == expected_pool_method_calls)
    assert (set(fake_pool.acquire.call_args.kwargs["bookmarks"])
            == expected_bookmarks_acquire)
    if routing and db is None:
        assert (
            set(fake_pool.update_routing_table.call_args.kwargs["bookmarks"])
            == expected_bookmarks_home_db_resolution
        )

    assert len(fake_pool.acquired_connection_mocks) == 1
    connection_mock = fake_pool.acquired_connection_mocks[0]
    connection_mock.run.assert_called_once()
    connection_run_call_kwargs = connection_mock.run.call_args.kwargs
    assert (set(connection_run_call_kwargs["bookmarks"])
            == expected_bookmarks_run)


@pytest.mark.parametrize("routing", (True, False))
@pytest.mark.parametrize("session_method", ("run", "get_server_info"))
@mark_sync_test
def test_last_bookmarks_does_not_leak_bookmark_managers_bookmarks(
    fake_pool, routing, session_method, mocker
):
    def bmm_get_bookmarks():
        return [f"bmm:bm1"]

    fake_pool.mock_add_spec(Neo4jPool if routing else BoltPool)

    bmm = mocker.Mock(spec=BookmarkManager)
    bmm.get_bookmarks.side_effect = bmm_get_bookmarks

    config = SessionConfig()
    config.bookmark_manager = bmm
    config.bookmarks = Bookmarks.from_raw_values(["session", "bookmarks"])
    with Session(fake_pool, config) as session:
        if session_method == "run":
            session.run("RETURN 1")
        elif session_method == "get_server_info":
            session._get_server_info()
        else:
            assert False
        last_bookmarks = session.last_bookmarks()

        assert last_bookmarks.raw_values == {"session", "bookmarks"}
    assert last_bookmarks.raw_values == {"session", "bookmarks"}
