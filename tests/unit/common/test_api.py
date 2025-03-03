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


from __future__ import annotations

import itertools
import typing as t

import pytest

import neo4j.api
from neo4j.exceptions import ConfigurationError


standard_ascii = [chr(i) for i in range(128)]
not_ascii = "♥O◘♦♥O◘♦"


def test_bookmark_is_deprecated() -> None:
    with pytest.deprecated_call():
        neo4j.Bookmark()


def test_bookmark_initialization_with_no_values() -> None:
    with pytest.deprecated_call():
        bookmark = neo4j.Bookmark()
    assert bookmark.values == frozenset()
    assert bool(bookmark) is False
    assert repr(bookmark) == "<Bookmark values={}>"


@pytest.mark.parametrize(
    "test_input, expected_values, expected_bool, expected_repr",
    [
        ((None,), frozenset(), False, "<Bookmark values={}>"),
        ((None, None), frozenset(), False, "<Bookmark values={}>"),
        (("bookmark1", None), frozenset({"bookmark1"}), True, "<Bookmark values={'bookmark1'}>"),
        (("bookmark1", None, "bookmark2", None), frozenset({"bookmark1", "bookmark2"}), True, "<Bookmark values={'bookmark1', 'bookmark2'}>"),
        ((None, "bookmark1", None, "bookmark2", None, None, "bookmark3"), frozenset({"bookmark1", "bookmark2", "bookmark3"}), True, "<Bookmark values={'bookmark1', 'bookmark2', 'bookmark3'}>"),
    ]
)
def test_bookmark_initialization_with_values_none(
    test_input, expected_values, expected_bool, expected_repr
) -> None:
    with pytest.deprecated_call():
        bookmark = neo4j.Bookmark(*test_input)
    assert bookmark.values == expected_values
    assert bool(bookmark) is expected_bool
    assert repr(bookmark) == expected_repr


@pytest.mark.parametrize(
    "test_input, expected_values, expected_bool, expected_repr",
    [
        (("",), frozenset(), False, "<Bookmark values={}>"),
        (("", ""), frozenset(), False, "<Bookmark values={}>"),
        (("bookmark1", ""), frozenset({"bookmark1"}), True, "<Bookmark values={'bookmark1'}>"),
        (("bookmark1", "", "bookmark2", ""), frozenset({"bookmark1", "bookmark2"}), True, "<Bookmark values={'bookmark1', 'bookmark2'}>"),
        (("", "bookmark1", "", "bookmark2", "", "", "bookmark3"), frozenset({"bookmark1", "bookmark2", "bookmark3"}), True, "<Bookmark values={'bookmark1', 'bookmark2', 'bookmark3'}>"),
    ]
)
def test_bookmark_initialization_with_values_empty_string(
    test_input, expected_values, expected_bool, expected_repr
) -> None:
    with pytest.deprecated_call():
        bookmark = neo4j.Bookmark(*test_input)
    assert bookmark.values == expected_values
    assert bool(bookmark) is expected_bool
    assert repr(bookmark) == expected_repr


@pytest.mark.parametrize(
    "test_input, expected_values, expected_bool, expected_repr",
    [
        (("bookmark1",), frozenset({"bookmark1"}), True, "<Bookmark values={'bookmark1'}>"),
        (("bookmark1", "bookmark2", "bookmark3"), frozenset({"bookmark1", "bookmark2", "bookmark3"}), True, "<Bookmark values={'bookmark1', 'bookmark2', 'bookmark3'}>"),
        (standard_ascii, frozenset(standard_ascii), True, "<Bookmark values={{'{values}'}}>".format(values="', '".join(standard_ascii)))
    ]
)
def test_bookmark_initialization_with_valid_strings(
    test_input, expected_values, expected_bool, expected_repr
) -> None:
    with pytest.deprecated_call():
        bookmark = neo4j.Bookmark(*test_input)
    assert bookmark.values == expected_values
    assert bool(bookmark) is expected_bool
    assert repr(bookmark) == expected_repr


_bm_input_mark = pytest.mark.parametrize(
    ("test_input", "expected"),
    [
        ((not_ascii,), ValueError),
        (("", not_ascii,), ValueError),
        (("bookmark1", chr(129),), ValueError),
    ]
)


@_bm_input_mark
def test_bookmark_initialization_with_invalid_strings(
    test_input: t.Tuple[str], expected
) -> None:
    with pytest.raises(expected):
        with pytest.warns(DeprecationWarning):
            neo4j.Bookmark(*test_input)


@_bm_input_mark
def test_bookmarks_initialization_with_invalid_strings(
    test_input: t.Tuple[str], expected
) -> None:
    with pytest.raises(expected):
        neo4j.Bookmarks.from_raw_values(test_input)


@pytest.mark.parametrize("test_as_generator", [True, False])
@pytest.mark.parametrize("values", (
    ("bookmark1", "bookmark2", "bookmark3"),
    {"bookmark1", "bookmark2", "bookmark3"},
    frozenset(("bookmark1", "bookmark2", "bookmark3")),
    ["bookmark1", "bookmark2", "bookmark3"],
    ("bookmark1", "bookmark2", "bookmark1"),
    ("bookmark1", ""),
    ("bookmark1",),
    (),
))
def test_bookmarks_raw_values(test_as_generator, values) -> None:
    expected = frozenset(values)
    if test_as_generator:
        values = (v for v in values)
    received = neo4j.Bookmarks().from_raw_values(values).raw_values
    assert isinstance(received, frozenset)
    assert received == expected


@pytest.mark.parametrize(("values", "exc_type"), (
    (("bookmark1", None), TypeError),
    ((neo4j.Bookmarks(),), TypeError),
    (neo4j.Bookmarks(), TypeError),
    ((None,), TypeError),
    (None, TypeError),
    ((False,), TypeError),
    (((),), TypeError),
    (([],), TypeError),
    ((dict(),), TypeError),
    ((set(),), TypeError),
    ((frozenset(),), TypeError),
    ((["bookmark1", "bookmark2"],), TypeError),
    ((not_ascii,), ValueError),
))
def test_bookmarks_invalid_raw_values(values, exc_type) -> None:
    with pytest.raises(exc_type):
        neo4j.Bookmarks().from_raw_values(values)


@pytest.mark.parametrize(("values", "expected_repr"), (
    (("bm1", "bm2"), "<Bookmarks values={'bm1', 'bm2'}>"),
    (("bm2", "bm1"), "<Bookmarks values={'bm1', 'bm2'}>"),
    (("bm42",), "<Bookmarks values={'bm42'}>"),
    ((), "<Bookmarks values={}>"),
))
def test_bookmarks_repr(values, expected_repr) -> None:
    bookmarks = neo4j.Bookmarks().from_raw_values(values)
    assert repr(bookmarks) == expected_repr


@pytest.mark.parametrize(("values1", "values2"), (
    (values
     for values in itertools.combinations_with_replacement(
         (
             ("bookmark1",),
             ("bookmark1", "bookmark2"),
             ("bookmark3",),
             (),
         ),
         2
     ))
))
def test_bookmarks_combination(values1, values2) -> None:
    bookmarks1 = neo4j.Bookmarks().from_raw_values(values1)
    bookmarks2 = neo4j.Bookmarks().from_raw_values(values2)
    bookmarks3 = bookmarks1 + bookmarks2
    assert bookmarks3.raw_values == (bookmarks2 + bookmarks1).raw_values
    assert bookmarks3.raw_values == frozenset(values1) | frozenset(values2)


@pytest.mark.parametrize(
    "test_input, expected_str, expected_repr",
    [
        ((), "", "Version()"),
        ((None,), "None", "Version(None,)"),
        (("3",), "3", "Version('3',)"),
        (("3", "0"), "3.0", "Version('3', '0')"),
        ((3,), "3", "Version(3,)"),
        ((3, 0), "3.0", "Version(3, 0)"),
        ((3, 0, 0), "3.0.0", "Version(3, 0, 0)"),
        ((3, 0, 0, 0), "3.0.0.0", "Version(3, 0, 0, 0)"),
    ]
)
def test_version_initialization(
    test_input, expected_str, expected_repr
) -> None:
    version = neo4j.Version(*test_input)
    assert str(version) == expected_str
    assert repr(version) == expected_repr


@pytest.mark.parametrize(
    "test_input, expected_str, expected_repr",
    [
        (bytearray([0, 0, 0, 0]), "0.0", "Version(0, 0)"),
        (bytearray([0, 0, 0, 1]), "1.0", "Version(1, 0)"),
        (bytearray([0, 0, 1, 0]), "0.1", "Version(0, 1)"),
        (bytearray([0, 0, 1, 1]), "1.1", "Version(1, 1)"),
        (bytearray([0, 0, 254, 254]), "254.254", "Version(254, 254)"),
    ]
)
def test_version_from_bytes_with_valid_bolt_version_handshake(
    test_input, expected_str, expected_repr
) -> None:
    version = neo4j.Version.from_bytes(test_input)
    assert str(version) == expected_str
    assert repr(version) == expected_repr


@pytest.mark.parametrize(
    "test_input, expected",
    [
        (bytearray([0, 0, 0]), ValueError),
        (bytearray([0, 0, 0, 0, 0]), ValueError),
        (bytearray([1, 0, 0, 0]), ValueError),
        (bytearray([0, 1, 0, 0]), ValueError),
        (bytearray([1, 1, 0, 0]), ValueError),
    ]
)
def test_version_from_bytes_with_not_valid_bolt_version_handshake(
    test_input, expected
) -> None:
    with pytest.raises(expected):
        _ = neo4j.Version.from_bytes(test_input)


@pytest.mark.parametrize(
    "test_input, expected",
    [
        ((), bytearray([0, 0, 0, 0])),
        ((0,), bytearray([0, 0, 0, 0])),
        ((1,), bytearray([0, 0, 0, 1])),
        ((0, 0), bytearray([0, 0, 0, 0])),
        ((1, 0), bytearray([0, 0, 0, 1])),
        ((1, 2), bytearray([0, 0, 2, 1])),
        ((255, 255), bytearray([0, 0, 255, 255])),
    ]
)
def test_version_to_bytes_with_valid_bolt_version(
    test_input, expected
) -> None:
    version = neo4j.Version(*test_input)
    assert version.to_bytes() == expected


def test_serverinfo_initialization() -> None:

    from neo4j.addressing import Address

    address = Address(("bolt://localhost", 7687))
    version = neo4j.Version(3, 0)

    server_info = neo4j.ServerInfo(address, version)
    assert server_info.address is address
    assert server_info.protocol_version is version
    with pytest.warns(DeprecationWarning):
        assert server_info.connection_id is None


@pytest.mark.parametrize(
    "test_input, expected_agent",
    [
        ({"server": "Neo4j/3.0.0"}, "Neo4j/3.0.0"),
        ({"server": "Neo4j/3.X.Y"}, "Neo4j/3.X.Y"),
        ({"server": "Neo4j/4.3.1"}, "Neo4j/4.3.1"),
    ]
)
@pytest.mark.parametrize("protocol_version", ((3, 0), (4, 3), (42, 1337)))
def test_serverinfo_with_metadata(
    test_input, expected_agent, protocol_version
) -> None:
    from neo4j.addressing import Address

    address = Address(("bolt://localhost", 7687))
    version = neo4j.Version(*protocol_version)

    server_info = neo4j.ServerInfo(address, version)

    server_info.update(test_input)

    assert server_info.agent == expected_agent
    assert server_info.protocol_version == version


@pytest.mark.parametrize(
    "test_input, expected_driver_type, expected_security_type, expected_error",
    [
        ("bolt://localhost:7676", neo4j.api.DRIVER_BOLT, neo4j.api.SECURITY_TYPE_NOT_SECURE, None),
        ("bolt+ssc://localhost:7676", neo4j.api.DRIVER_BOLT, neo4j.api.SECURITY_TYPE_SELF_SIGNED_CERTIFICATE, None),
        ("bolt+s://localhost:7676", neo4j.api.DRIVER_BOLT, neo4j.api.SECURITY_TYPE_SECURE, None),
        ("neo4j://localhost:7676", neo4j.api.DRIVER_NEO4J, neo4j.api.SECURITY_TYPE_NOT_SECURE, None),
        ("neo4j+ssc://localhost:7676", neo4j.api.DRIVER_NEO4J, neo4j.api.SECURITY_TYPE_SELF_SIGNED_CERTIFICATE, None),
        ("neo4j+s://localhost:7676", neo4j.api.DRIVER_NEO4J, neo4j.api.SECURITY_TYPE_SECURE, None),
        ("undefined://localhost:7676", None, None, ConfigurationError),
        ("localhost:7676", None, None, ConfigurationError),
        ("://localhost:7676", None, None, ConfigurationError),
        ("bolt+routing://localhost:7676", neo4j.api.DRIVER_NEO4J, neo4j.api.SECURITY_TYPE_NOT_SECURE, ConfigurationError),
        ("bolt://username@localhost:7676", None, None, ConfigurationError),
        ("bolt://username:password@localhost:7676", None, None, ConfigurationError),
    ]
)
def test_uri_scheme(
    test_input, expected_driver_type, expected_security_type, expected_error
) -> None:
    if expected_error:
        with pytest.raises(expected_error):
            neo4j.api.parse_neo4j_uri(test_input)
    else:
        driver_type, security_type, parsed = neo4j.api.parse_neo4j_uri(test_input)
        assert driver_type == expected_driver_type
        assert security_type == expected_security_type


def test_parse_routing_context() -> None:
    context = neo4j.api.parse_routing_context(query="name=molly&color=white")
    assert context == {"name": "molly", "color": "white"}


def test_parse_routing_context_should_error_when_value_missing() -> None:
    with pytest.raises(ConfigurationError):
        neo4j.api.parse_routing_context("name=&color=white")


def test_parse_routing_context_should_error_when_key_duplicate() -> None:
    with pytest.raises(ConfigurationError):
        neo4j.api.parse_routing_context("name=molly&name=white")
