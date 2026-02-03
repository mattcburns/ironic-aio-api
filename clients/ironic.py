"""Ironic client wrapper."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from openstack import connection as os_connection

from config import Settings

if TYPE_CHECKING:
    from openstack.connection import Connection
    from openstack.baremetal.v1.node import Node

logger = logging.getLogger(__name__)


class IronicClientError(RuntimeError):
    """Represents errors raised by the Ironic client wrapper."""


class IronicClient:
    """Wrapper around OpenStack SDK for Ironic operations."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def get_connection(self) -> Connection:
        """Get or create OpenStack connection."""

        try:
            connection = os_connection.Connection(
                auth_type="none",
                endpoint_override=self.settings.ironic_api_url,
                baremetal_endpoint_override=self.settings.ironic_api_url,
                baremetal_api_version=self.settings.ironic_api_version,
            )
        except Exception as exc:  # pragma: no cover - depends on SDK internals
            logger.exception("Failed to create OpenStack connection")
            raise IronicClientError("Failed to create OpenStack connection") from exc

        return connection

    async def list_nodes(self) -> list[Node]:
        """List all Ironic nodes."""

        # TODO: Use the OpenStack SDK to list Ironic nodes.
        raise NotImplementedError("Ironic API call not implemented yet.")

    async def get_node(self, node_id: str) -> Node:
        """Get a specific node by ID or name."""

        # TODO: Use the OpenStack SDK to fetch a specific Ironic node.
        raise NotImplementedError("Ironic API call not implemented yet.")

    async def check_connectivity(self) -> bool:
        """Check if Ironic API is reachable."""

        try:
            await self.get_connection()
            # TODO: Replace this with a lightweight Ironic API call.
            return True
        except IronicClientError:
            return False
        except Exception:
            logger.exception("Unexpected error while checking Ironic connectivity")
            return False
