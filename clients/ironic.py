# Copyright (C) 2026 Matthew Burns
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published
# by the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""Ironic client wrapper."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import httpx
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

    def _get_http_client_auth(self) -> httpx.BasicAuth | None:
        """Get basic auth credentials if configured.

        Returns:
            httpx.BasicAuth object if credentials are configured, None otherwise
        """
        if (
            self.settings.ironic_basic_auth_username
            and self.settings.ironic_basic_auth_password
        ):
            return httpx.BasicAuth(
                self.settings.ironic_basic_auth_username,
                self.settings.ironic_basic_auth_password,
            )
        return None

    def _create_http_client(self) -> httpx.AsyncClient:
        """Create a pre-configured httpx AsyncClient with auth and SSL settings.

        Returns:
            Configured httpx.AsyncClient for Ironic API requests
        """
        return httpx.AsyncClient(
            auth=self._get_http_client_auth(),
            verify=not self.settings.ironic_skip_ca_verification,
        )

    async def get_connection(self) -> Connection:
        """Get or create OpenStack connection."""
        connection_kwargs = {
            "endpoint_override": self.settings.ironic_api_url,
            "baremetal_endpoint_override": self.settings.ironic_api_url,
            "baremetal_api_version": self.settings.ironic_api_version,
            "verify": not self.settings.ironic_skip_ca_verification,
        }
        if (
            self.settings.ironic_basic_auth_username
            and self.settings.ironic_basic_auth_password
        ):
            connection_kwargs["auth_type"] = "http_basic"
            connection_kwargs["auth"] = {
                "username": self.settings.ironic_basic_auth_username,
                "password": self.settings.ironic_basic_auth_password,
            }
        else:
            connection_kwargs["auth_type"] = "none"

        try:
            connection = os_connection.Connection(**connection_kwargs)
        except Exception as exc:  # pragma: no cover - depends on SDK internals
            logger.exception("Failed to create OpenStack connection")
            raise IronicClientError("Failed to create OpenStack connection") from exc

        return connection

    async def list_nodes(self) -> list[Node]:
        """List all Ironic nodes."""
        try:
            connection = await self.get_connection()
            nodes = connection.baremetal.nodes()
            return list(nodes)
        except Exception as exc:
            logger.exception("Failed to list Ironic nodes")
            raise IronicClientError("Failed to list Ironic nodes") from exc

    async def get_node(self, node_id: str, ignore_missing: bool = False) -> Node | None:
        """Get a specific node by ID or name."""
        try:
            connection = await self.get_connection()
            if ignore_missing:
                node = connection.baremetal.get_node(
                    node_id,
                    ignore_missing=ignore_missing,
                )
            else:
                node = connection.baremetal.get_node(node_id)
            return node
        except Exception as exc:
            logger.exception(f"Failed to get node {node_id}")
            raise IronicClientError(f"Failed to get node {node_id}") from exc

    async def get_node_by_name(self, name: str) -> Node | None:
        """Get a node by name.

        Args:
            name: Name of the node to retrieve

        Returns:
            Node if found, None otherwise
        """
        try:
            connection = await self.get_connection()
            node = connection.baremetal.find_node(name, ignore_missing=True)
            return node
        except Exception as exc:
            logger.exception(f"Failed to get node by name {name}")
            raise IronicClientError(f"Failed to get node by name {name}") from exc

    async def create_node(
        self,
        name: str,
        driver: str,
        driver_info: dict,
        resource_class: str | None = None,
        properties: dict | None = None,
    ) -> Node:
        """Create a new node in Ironic.

        Args:
            name: Unique name for the node
            driver: Driver to use (e.g., 'redfish')
            driver_info: Driver-specific configuration
            resource_class: Resource class for the node
            properties: Node properties (CPU, memory, disk, etc.)

        Returns:
            Created Node object
        """
        try:
            connection = await self.get_connection()
            node_data = {
                "name": name,
                "driver": driver,
                "driver_info": driver_info,
            }
            if resource_class:
                node_data["resource_class"] = resource_class
            if properties:
                node_data["properties"] = properties

            node = connection.baremetal.create_node(**node_data)
            return node
        except Exception as exc:
            logger.exception(f"Failed to create node {name}")
            raise IronicClientError(f"Failed to create node {name}") from exc

    async def add_node_port(
        self,
        node_id: str,
        mac_address: str,
        extra: dict | None = None,
    ) -> object:
        """Add a network port to a node.

        Args:
            node_id: UUID of the node
            mac_address: MAC address of the port
            extra: Additional port configuration

        Returns:
            Created Port object
        """
        try:
            connection = await self.get_connection()
            port_data = {
                "node_uuid": node_id,
                "address": mac_address,
            }
            if extra:
                port_data["extra"] = extra

            port = connection.baremetal.create_port(**port_data)
            return port
        except Exception as exc:
            logger.exception(f"Failed to add port to node {node_id}")
            raise IronicClientError(f"Failed to add port to node {node_id}") from exc

    async def validate_node(self, node_id: str) -> dict:
        """Validate node driver (test BMC connectivity).

        Args:
            node_id: UUID of the node to validate

        Returns:
            Validation result dictionary
        """
        try:
            connection = await self.get_connection()
            result = connection.baremetal.validate_node(node_id)
            return result
        except Exception as exc:
            logger.exception(f"Failed to validate node {node_id}")
            raise IronicClientError(f"Failed to validate node {node_id}") from exc

    async def set_node_provision_state(
        self,
        node_id: str,
        target_state: str,
    ) -> Node:
        """Set node provision state target.

        Args:
            node_id: UUID of the node
            target_state: Target provision state (e.g., 'manage', 'provide', 'active', 'deleted')

        Returns:
            Updated Node object

        Raises:
            IronicClientError: If the state transition fails
        """
        try:
            connection = await self.get_connection()
            node = connection.baremetal.set_node_provision_state(
                node_id,
                target_state
            )
            return node
        except Exception as exc:
            logger.exception(f"Failed to set provision state for node {node_id}")
            raise IronicClientError(
                f"Failed to set provision state for node {node_id} to {target_state}"
            ) from exc

    async def check_connectivity(self) -> bool:
        """Check if Ironic API is reachable."""

        try:
            await self.get_connection()

            # Make a lightweight GET request to /v1/ endpoint to verify connectivity
            # and check API version
            url = f"{self.settings.ironic_api_url.rstrip('/')}/v1/"

            async with self._create_http_client() as client:
                response = await client.get(url, timeout=10.0)
                response.raise_for_status()

                # Parse the API version from the response
                data = response.json()
                api_version = data.get("version", {}).get("version", "unknown")
                logger.info(f"Ironic API version: {api_version}")

                # Compare with configured version
                configured_version = self.settings.ironic_api_version
                if self._is_version_older(api_version, configured_version):
                    logger.error(
                        f"Ironic API version {api_version} is older than configured "
                        f"version {configured_version}"
                    )

            return True
        except IronicClientError:
            return False
        except Exception:
            logger.exception("Unexpected error while checking Ironic connectivity")
            return False

    def _is_version_older(self, current: str, required: str) -> bool:
        """Compare two version strings to check if current is older than required.

        Args:
            current: Current API version string (e.g., "1.82")
            required: Required API version string (e.g., "1.82")

        Returns:
            True if current version is older than required version
        """
        try:
            # Parse version strings like "1.82" into tuples (1, 82)
            current_parts = tuple(int(x) for x in current.split("."))
            required_parts = tuple(int(x) for x in required.split("."))
            return current_parts < required_parts
        except (ValueError, AttributeError):
            # If we can't parse versions, assume it's not older
            logger.warning(f"Unable to compare versions: {current} vs {required}")
            return False
