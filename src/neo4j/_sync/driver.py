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

import typing as t


if t.TYPE_CHECKING:
    import typing_extensions as te

    import ssl

from .._async_compat.util import Util
from .._conf import (
    Config,
    PoolConfig,
    SessionConfig,
    TrustAll,
    TrustStore,
    WorkspaceConfig,
)
from .._meta import (
    deprecation_warn,
    experimental,
    experimental_warn,
    unclosed_resource_warn,
)
from ..addressing import Address
from ..api import (
    Auth,
    BookmarkManager,
    Bookmarks,
    DRIVER_BOLT,
    DRIVER_NEO4J,
    parse_neo4j_uri,
    parse_routing_context,
    READ_ACCESS,
    SECURITY_TYPE_SECURE,
    SECURITY_TYPE_SELF_SIGNED_CERTIFICATE,
    ServerInfo,
    TRUST_ALL_CERTIFICATES,
    TRUST_SYSTEM_CA_SIGNED_CERTIFICATES,
    URI_SCHEME_BOLT,
    URI_SCHEME_BOLT_SECURE,
    URI_SCHEME_BOLT_SELF_SIGNED_CERTIFICATE,
    URI_SCHEME_NEO4J,
    URI_SCHEME_NEO4J_SECURE,
    URI_SCHEME_NEO4J_SELF_SIGNED_CERTIFICATE,
)
from .bookmark_manager import (
    Neo4jBookmarkManager,
    TBmConsumer as _TBmConsumer,
    TBmSupplier as _TBmSupplier,
)
from .work import Session


class GraphDatabase:
    """Accessor for :class:`neo4j.Driver` construction.
    """

    if t.TYPE_CHECKING:

        @classmethod
        def driver(
            cls,
            uri: str,
            *,
            auth: t.Union[t.Tuple[t.Any, t.Any], Auth, None] = ...,
            max_connection_lifetime: float = ...,
            max_connection_pool_size: int = ...,
            connection_timeout: float = ...,
            trust: t.Union[
                te.Literal["TRUST_ALL_CERTIFICATES"],
                te.Literal["TRUST_SYSTEM_CA_SIGNED_CERTIFICATES"]
            ] = ...,
            resolver: t.Union[
                t.Callable[[Address], t.Iterable[Address]],
                t.Callable[[Address], t.Union[t.Iterable[Address]]],
            ] = ...,
            encrypted: bool = ...,
            trusted_certificates: TrustStore = ...,
            ssl_context: ssl.SSLContext = ...,
            user_agent: str = ...,
            keep_alive: bool = ...,

            # undocumented/unsupported options
            # they may be change or removed any time without prior notice
            connection_acquisition_timeout: float = ...,
            max_transaction_retry_time: float = ...,
            initial_retry_delay: float = ...,
            retry_delay_multiplier: float = ...,
            retry_delay_jitter_factor: float = ...,
            database: t.Optional[str] = ...,
            fetch_size: int = ...,
            impersonated_user: t.Optional[str] = ...,
            bookmark_manager: t.Union[BookmarkManager,
                                      BookmarkManager, None] = ...
        ) -> Driver:
            ...

    else:

        @classmethod
        def driver(cls, uri, *, auth=None, **config) -> Driver:
            """Create a driver.

            :param uri: the connection URI for the driver, see :ref:`uri-ref` for available URIs.
            :param auth: the authentication details, see :ref:`auth-ref` for available authentication details.
            :param config: driver configuration key-word arguments, see :ref:`driver-configuration-ref` for available key-word arguments.
            """

            driver_type, security_type, parsed = parse_neo4j_uri(uri)

            # TODO: 6.0 - remove "trust" config option
            if "trust" in config.keys():
                if config["trust"] not in (
                    TRUST_ALL_CERTIFICATES,
                    TRUST_SYSTEM_CA_SIGNED_CERTIFICATES
                ):
                    from ..exceptions import ConfigurationError
                    raise ConfigurationError(
                        "The config setting `trust` values are {!r}"
                        .format(
                            [
                                TRUST_ALL_CERTIFICATES,
                                TRUST_SYSTEM_CA_SIGNED_CERTIFICATES,
                            ]
                        )
                    )

            if ("trusted_certificates" in config.keys()
                and not isinstance(config["trusted_certificates"],
                                   TrustStore)):
                raise ConnectionError(
                    "The config setting `trusted_certificates` must be of "
                    "type neo4j.TrustAll, neo4j.TrustCustomCAs, or"
                    "neo4j.TrustSystemCAs but was {}".format(
                        type(config["trusted_certificates"])
                    )
                )

            if (security_type in [SECURITY_TYPE_SELF_SIGNED_CERTIFICATE, SECURITY_TYPE_SECURE]
                and ("encrypted" in config.keys()
                     or "trust" in config.keys()
                     or "trusted_certificates" in config.keys()
                     or "ssl_context" in config.keys())):
                from ..exceptions import ConfigurationError

                # TODO: 6.0 - remove "trust" from error message
                raise ConfigurationError(
                    'The config settings "encrypted", "trust", '
                    '"trusted_certificates", and "ssl_context" can only be '
                    "used with the URI schemes {!r}. Use the other URI "
                    "schemes {!r} for setting encryption settings."
                    .format(
                        [
                            URI_SCHEME_BOLT,
                            URI_SCHEME_NEO4J,
                        ],
                        [
                            URI_SCHEME_BOLT_SELF_SIGNED_CERTIFICATE,
                            URI_SCHEME_BOLT_SECURE,
                            URI_SCHEME_NEO4J_SELF_SIGNED_CERTIFICATE,
                            URI_SCHEME_NEO4J_SECURE,
                        ]
                    )
                )

            if security_type == SECURITY_TYPE_SECURE:
                config["encrypted"] = True
            elif security_type == SECURITY_TYPE_SELF_SIGNED_CERTIFICATE:
                config["encrypted"] = True
                config["trusted_certificates"] = TrustAll()

            assert driver_type in (DRIVER_BOLT, DRIVER_NEO4J)
            if driver_type == DRIVER_BOLT:
                if parse_routing_context(parsed.query):
                    deprecation_warn(
                        "Creating a direct driver (`bolt://` scheme) with "
                        "routing context (URI parameters) is deprecated. They "
                        "will be ignored. This will raise an error in a "
                        'future release. Given URI "{}"'.format(uri),
                        stack_level=2
                    )
                    # TODO: 6.0 - raise instead of warning
                    # raise ValueError(
                    #     'Routing parameters are not supported with scheme '
                    #     '"bolt". Given URI "{}".'.format(uri)
                    # )
                return cls.bolt_driver(parsed.netloc, auth=auth, **config)
            # else driver_type == DRIVER_NEO4J
            routing_context = parse_routing_context(parsed.query)
            return cls.neo4j_driver(parsed.netloc, auth=auth,
                                    routing_context=routing_context, **config)

    @classmethod
    @experimental(
        "The bookmark manager feature is experimental. "
        "It might be changed or removed any time even without prior notice."
    )
    def bookmark_manager(
        cls,
        initial_bookmarks: t.Union[None, Bookmarks, t.Iterable[str]] = None,
        bookmarks_supplier: t.Optional[_TBmSupplier] = None,
        bookmarks_consumer: t.Optional[_TBmConsumer] = None
    ) -> BookmarkManager:
        """Create a :class:`.BookmarkManager` with default implementation.

        Basic usage example to configure sessions with the built-in bookmark
        manager implementation so that all work is automatically causally
        chained (i.e., all reads can observe all previous writes even in a
        clustered setup)::

            import neo4j


            # omitting closing the driver for brevity
            driver = neo4j.GraphDatabase.driver(...)
            bookmark_manager = neo4j.GraphDatabase.bookmark_manager(...)

            with driver.session(
                bookmark_manager=bookmark_manager
            ) as session1:
                with driver.session(
                    bookmark_manager=bookmark_manager,
                    access_mode=neo4j.READ_ACCESS
                ) as session2:
                    result1 = session1.run("<WRITE_QUERY>")
                    result1.consume()
                    # READ_QUERY is guaranteed to see what WRITE_QUERY wrote.
                    result2 = session2.run("<READ_QUERY>")
                    result2.consume()

        This is a very contrived example, and in this particular case, having
        both queries in the same session has the exact same effect and might
        even be more performant. However, when dealing with sessions spanning
        multiple threads, Tasks, processes, or even hosts, the bookmark
        manager can come in handy as sessions are not safe to be used
        concurrently.

        :param initial_bookmarks:
            The initial set of bookmarks. The returned bookmark manager will
            use this to initialize its internal bookmarks.
        :param bookmarks_supplier:
            Function which will be called every time the default bookmark
            manager's method :meth:`.BookmarkManager.get_bookmarks`
            gets called.
            The function takes no arguments and must return a
            :class:`.Bookmarks` object. The result of ``bookmarks_supplier``
            will then be concatenated with the internal set of bookmarks and
            used to configure the session in creation. It will, however, not
            update the internal set of bookmarks.
        :param bookmarks_consumer:
            Function which will be called whenever the set of bookmarks
            handled by the bookmark manager gets updated with the new
            internal bookmark set. It will receive the new set of bookmarks
            as a :class:`.Bookmarks` object and return :data:`None`.

        :returns: A default implementation of :class:`BookmarkManager`.

        **This is experimental.** (See :ref:`filter-warnings-ref`)
        It might be changed or removed any time even without prior notice.

        .. versionadded:: 5.0

        .. versionchanged:: 5.3
            The bookmark manager no longer tracks bookmarks per database.
            This effectively changes the signature of almost all bookmark
            manager related methods:

            * ``initial_bookmarks`` is no longer a mapping from database name
              to bookmarks but plain bookmarks.
            * ``bookmarks_supplier`` no longer receives the database name as
              an argument.
            * ``bookmarks_consumer`` no longer receives the database name as
              an argument.
        """
        return Neo4jBookmarkManager(
            initial_bookmarks=initial_bookmarks,
            bookmarks_supplier=bookmarks_supplier,
            bookmarks_consumer=bookmarks_consumer
        )

    @classmethod
    def bolt_driver(cls, target, *, auth=None, **config):
        """ Create a driver for direct Bolt server access that uses
        socket I/O and thread-based concurrency.
        """
        from .._exceptions import (
            BoltHandshakeError,
            BoltSecurityError,
        )

        try:
            return BoltDriver.open(target, auth=auth, **config)
        except (BoltHandshakeError, BoltSecurityError) as error:
            from ..exceptions import ServiceUnavailable
            raise ServiceUnavailable(str(error)) from error

    @classmethod
    def neo4j_driver(cls, *targets, auth=None, routing_context=None, **config):
        """ Create a driver for routing-capable Neo4j service access
        that uses socket I/O and thread-based concurrency.
        """
        from .._exceptions import (
            BoltHandshakeError,
            BoltSecurityError,
        )

        try:
            return Neo4jDriver.open(*targets, auth=auth, routing_context=routing_context, **config)
        except (BoltHandshakeError, BoltSecurityError) as error:
            from ..exceptions import ServiceUnavailable
            raise ServiceUnavailable(str(error)) from error


class _Direct:

    default_host = "localhost"
    default_port = 7687

    default_target = ":"

    def __init__(self, address):
        self._address = address

    @property
    def address(self):
        return self._address

    @classmethod
    def parse_target(cls, target):
        """ Parse a target string to produce an address.
        """
        if not target:
            target = cls.default_target
        address = Address.parse(target, default_host=cls.default_host,
                                default_port=cls.default_port)
        return address


class _Routing:

    default_host = "localhost"
    default_port = 7687

    default_targets = ": :17601 :17687"

    def __init__(self, initial_addresses):
        self._initial_addresses = initial_addresses

    @property
    def initial_addresses(self):
        return self._initial_addresses

    @classmethod
    def parse_targets(cls, *targets):
        """ Parse a sequence of target strings to produce an address
        list.
        """
        targets = " ".join(targets)
        if not targets:
            targets = cls.default_targets
        addresses = Address.parse_list(targets, default_host=cls.default_host, default_port=cls.default_port)
        return addresses


class Driver:
    """ Base class for all types of :class:`neo4j.Driver`, instances of
    which are used as the primary access point to Neo4j.
    """

    #: Connection pool
    _pool: t.Any = None

    #: Flag if the driver has been closed
    _closed = False

    def __init__(self, pool, default_workspace_config):
        assert pool is not None
        assert default_workspace_config is not None
        self._pool = pool
        self._default_workspace_config = default_workspace_config

    def __enter__(self) -> Driver:
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def __del__(self):
        if not self._closed:
            unclosed_resource_warn(self)
        # TODO: 6.0 - remove this
        if not self._closed:
            if not Util.is_async_code:
                deprecation_warn(
                    "Relying on Driver's destructor to close the session "
                    "is deprecated. Please make sure to close the session. "
                    "Use it as a context (`with` statement) or make sure to "
                    "call `.close()` explicitly. Future versions of the "
                    "driver will not close drivers automatically."
                )
                self.close()

    @property
    def encrypted(self) -> bool:
        """Indicate whether the driver was configured to use encryption."""
        return bool(self._pool.pool_config.encrypted)

    if t.TYPE_CHECKING:

        def session(
            self,
            connection_acquisition_timeout: float = ...,
            max_transaction_retry_time: float = ...,
            database: t.Optional[str] = ...,
            fetch_size: int = ...,
            impersonated_user: t.Optional[str] = ...,
            bookmarks: t.Union[t.Iterable[str], Bookmarks, None] = ...,
            default_access_mode: str = ...,
            bookmark_manager: t.Union[BookmarkManager,
                                      BookmarkManager, None] = ...,

            # undocumented/unsupported options
            # they may be change or removed any time without prior notice
            initial_retry_delay: float = ...,
            retry_delay_multiplier: float = ...,
            retry_delay_jitter_factor: float = ...
        ) -> Session:
            ...

    else:

        def session(self, **config) -> Session:
            """Create a session, see :ref:`session-construction-ref`

            :param config: session configuration key-word arguments,
                see :ref:`session-configuration-ref` for available
                key-word arguments.

            :returns: new :class:`neo4j.Session` object
            """
            raise NotImplementedError

    def close(self) -> None:
        """ Shut down, closing any open connections in the pool.
        """
        self._pool.close()
        self._closed = True

    if t.TYPE_CHECKING:

        def verify_connectivity(
            self,
            # all arguments are experimental
            # they may be change or removed any time without prior notice
            session_connection_timeout: float = ...,
            connection_acquisition_timeout: float = ...,
            max_transaction_retry_time: float = ...,
            database: t.Optional[str] = ...,
            fetch_size: int = ...,
            impersonated_user: t.Optional[str] = ...,
            bookmarks: t.Union[t.Iterable[str], Bookmarks, None] = ...,
            default_access_mode: str = ...,
            bookmark_manager: t.Union[BookmarkManager,
                                      BookmarkManager, None] = ...,

            # undocumented/unsupported options
            initial_retry_delay: float = ...,
            retry_delay_multiplier: float = ...,
            retry_delay_jitter_factor: float = ...
        ) -> None:
            ...

    else:

        # TODO: 6.0 - remove config argument
        def verify_connectivity(self, **config) -> None:
            """Verify that the driver can establish a connection to the server.

            This verifies if the driver can establish a reading connection to a
            remote server or a cluster. Some data will be exchanged.

            .. note::
                Even if this method raises an exception, the driver still needs
                to be closed via :meth:`close` to free up all resources.

            :param config: accepts the same configuration key-word arguments as
                :meth:`session`.

                .. warning::
                    All configuration key-word arguments are experimental.
                    They might be changed or removed in any future version
                    without prior notice.

            :raises DriverError: if the driver cannot connect to the remote.
                Use the exception to further understand the cause of the
                connectivity problem.

            .. versionchanged:: 5.0
                The undocumented return value has been removed.
                If you need information about the remote server, use
                :meth:`get_server_info` instead.
            """
            if config:
                experimental_warn(
                    "All configuration key-word arguments to "
                    "verify_connectivity() are experimental. They might be "
                    "changed or removed in any future version without prior "
                    "notice."
                )
            with self.session(**config) as session:
                session._get_server_info()

    if t.TYPE_CHECKING:

        def get_server_info(
            self,
            # all arguments are experimental
            # they may be change or removed any time without prior notice
            session_connection_timeout: float = ...,
            connection_acquisition_timeout: float = ...,
            max_transaction_retry_time: float = ...,
            database: t.Optional[str] = ...,
            fetch_size: int = ...,
            impersonated_user: t.Optional[str] = ...,
            bookmarks: t.Union[t.Iterable[str], Bookmarks, None] = ...,
            default_access_mode: str = ...,
            bookmark_manager: t.Union[BookmarkManager,
                                      BookmarkManager, None] = ...,

            # undocumented/unsupported options
            initial_retry_delay: float = ...,
            retry_delay_multiplier: float = ...,
            retry_delay_jitter_factor: float = ...
        ) -> ServerInfo:
            ...

    else:

        def get_server_info(self, **config) -> ServerInfo:
            """Get information about the connected Neo4j server.

            Try to establish a working read connection to the remote server or
            a member of a cluster and exchange some data. Then return the
            contacted server's information.

            In a cluster, there is no guarantee about which server will be
            contacted.

            .. note::
                Even if this method raises an exception, the driver still needs
                to be closed via :meth:`close` to free up all resources.

            :param config: accepts the same configuration key-word arguments as
                :meth:`session`.

                .. warning::
                    All configuration key-word arguments are experimental.
                    They might be changed or removed in any future version
                    without prior notice.

            :raises DriverError: if the driver cannot connect to the remote.
                Use the exception to further understand the cause of the
                connectivity problem.

            .. versionadded:: 5.0
            """
            if config:
                experimental_warn(
                    "All configuration key-word arguments to "
                    "verify_connectivity() are experimental. They might be "
                    "changed or removed in any future version without prior "
                    "notice."
                )
            with self.session(**config) as session:
                return session._get_server_info()

    @experimental("Feature support query, based on Bolt protocol version and Neo4j server version will change in the future.")
    def supports_multi_db(self) -> bool:
        """ Check if the server or cluster supports multi-databases.

        :returns: Returns true if the server or cluster the driver connects to
            supports multi-databases, otherwise false.

        .. note::
            Feature support query, based on Bolt Protocol Version and Neo4j
            server version will change in the future.
        """
        with self.session() as session:
            session._connect(READ_ACCESS)
            assert session._connection
            return session._connection.supports_multiple_databases


class BoltDriver(_Direct, Driver):
    """:class:`.BoltDriver` is instantiated for ``bolt`` URIs and
    addresses a single database machine. This may be a standalone server or
    could be a specific member of a cluster.

    Connections established by a :class:`.BoltDriver` are always made to
    the exact host and port detailed in the URI.

    This class is not supposed to be instantiated externally. Use
    :meth:`GraphDatabase.driver` instead.
    """

    @classmethod
    def open(cls, target, *, auth=None, **config):
        """
        :param target:
        :param auth:
        :param config: The values that can be specified are found in :class: `neo4j.PoolConfig` and :class: `neo4j.WorkspaceConfig`

        :returns:
        :rtype: :class: `neo4j.BoltDriver`
        """
        from .io import BoltPool
        address = cls.parse_target(target)
        pool_config, default_workspace_config = Config.consume_chain(config, PoolConfig, WorkspaceConfig)
        pool = BoltPool.open(address, auth=auth, pool_config=pool_config, workspace_config=default_workspace_config)
        return cls(pool, default_workspace_config)

    def __init__(self, pool, default_workspace_config):
        _Direct.__init__(self, pool.address)
        Driver.__init__(self, pool, default_workspace_config)
        self._default_workspace_config = default_workspace_config

    if not t.TYPE_CHECKING:

        def session(self, **config) -> Session:
            """
            :param config: The values that can be specified are found in
                :class: `neo4j.SessionConfig`

            :returns:
            :rtype: :class: `neo4j.Session`
            """
            session_config = SessionConfig(self._default_workspace_config,
                                           config)
            return Session(self._pool, session_config)


class Neo4jDriver(_Routing, Driver):
    """:class:`.Neo4jDriver` is instantiated for ``neo4j`` URIs. The
    routing behaviour works in tandem with Neo4j's `Causal Clustering
    <https://neo4j.com/docs/operations-manual/current/clustering/>`_
    feature by directing read and write behaviour to appropriate
    cluster members.

    This class is not supposed to be instantiated externally. Use
    :meth:`GraphDatabase.driver` instead.
    """

    @classmethod
    def open(cls, *targets, auth=None, routing_context=None, **config):
        from .io import Neo4jPool
        addresses = cls.parse_targets(*targets)
        pool_config, default_workspace_config = Config.consume_chain(config, PoolConfig, WorkspaceConfig)
        pool = Neo4jPool.open(*addresses, auth=auth, routing_context=routing_context, pool_config=pool_config, workspace_config=default_workspace_config)
        return cls(pool, default_workspace_config)

    def __init__(self, pool, default_workspace_config):
        _Routing.__init__(self, [pool.address])
        Driver.__init__(self, pool, default_workspace_config)

    if not t.TYPE_CHECKING:

        def session(self, **config) -> Session:
            session_config = SessionConfig(self._default_workspace_config,
                                           config)
            return Session(self._pool, session_config)
