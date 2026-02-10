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

from datetime import datetime, timezone
from typing import Optional

from fastapi import HTTPException

from clients.ironic import IronicClient, IronicClientError
from schemas.server import ServerListResponse, ServerSummary


class ServerService:
    """Server management business logic."""

    def __init__(self, ironic_client: IronicClient):
        """Initialize server service.

        Args:
            ironic_client: Client for interacting with Ironic API
        """
        self.ironic = ironic_client

    async def list_servers(
        self,
        provision_state: Optional[str] = None,
        resource_class: Optional[str] = None,
        available_only: bool = False,
        page: int = 1,
        page_size: int = 50
    ) -> ServerListResponse:
        """
        List servers with optional filtering.

        Args:
            provision_state: Filter by provisioning state
            resource_class: Filter by resource class
            available_only: Only return servers available for provisioning
            page: Page number (1-indexed)
            page_size: Number of servers per page

        Returns:
            ServerListResponse with filtered servers and pagination info
        """
        try:
            nodes = await self.ironic.list_nodes()
        except IronicClientError as exc:
            raise HTTPException(
                status_code=502,
                detail="Failed to communicate with Ironic",
            ) from exc

        if provision_state:
            nodes = [
                node
                for node in nodes
                if getattr(node, "provision_state", None) == provision_state
            ]
        if resource_class:
            nodes = [
                node
                for node in nodes
                if getattr(node, "resource_class", None) == resource_class
            ]
        if available_only:
            nodes = [node for node in nodes if self._is_available(node)]

        all_servers = [self._node_to_summary(node) for node in nodes]

        # Apply pagination
        total = len(all_servers)
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paginated_servers = all_servers[start_idx:end_idx]

        return ServerListResponse(
            servers=paginated_servers,
            total=total,
            page=page,
            page_size=page_size
        )

    async def get_server(self, server_id: str) -> ServerSummary:
        """
        Get a single server by ID or name.

        Args:
            server_id: Server UUID or name

        Returns:
            ServerSummary with server details

        Raises:
            HTTPException: If server not found or Ironic is unreachable
        """
        try:
            node = await self.ironic.get_node(server_id, ignore_missing=True)
        except IronicClientError as exc:
            raise HTTPException(
                status_code=502,
                detail="Failed to communicate with Ironic",
            ) from exc

        if node is None:
            raise HTTPException(
                status_code=404,
                detail=f"Server '{server_id}' not found",
            )

        return self._node_to_summary(node)

    def _is_available(self, node) -> bool:
        """
        Determine if a node is available for provisioning.

        Business logic: a server is available if:
        - Provision state is 'available'
        - Not in maintenance mode
        - Power state is 'power off'

        Args:
            node: Ironic node object

        Returns:
            True if node is available for provisioning, False otherwise
        """
        provision_state = getattr(node, "provision_state", None)
        maintenance = getattr(node, "maintenance", None)
        power_state = getattr(node, "power_state", None)

        if provision_state is None or maintenance is None or power_state is None:
            return False

        return (
            provision_state == "available"
            and maintenance is False
            and power_state == "power off"
        )

    def _node_to_summary(self, node) -> ServerSummary:
        """
        Transform an Ironic node to ServerSummary.

        Args:
            node: Ironic node object

        Returns:
            ServerSummary with transformed data
        """
        node_id = getattr(node, "id", None)
        if not isinstance(node_id, str) or not node_id:
            node_id = getattr(node, "uuid", None)
        if not isinstance(node_id, str) or not node_id:
            node_id = getattr(node, "name", "unknown")

        provision_state = getattr(node, "provision_state", None) or "unknown"
        power_state = getattr(node, "power_state", None)
        resource_class = getattr(node, "resource_class", None)
        properties = getattr(node, "properties", None) or {}

        created_at = self._parse_datetime(getattr(node, "created_at", None))
        updated_at = self._parse_datetime(getattr(node, "updated_at", None))

        name = getattr(node, "name", None)
        if not isinstance(name, str) or not name:
            name = str(node_id)

        return ServerSummary(
            id=str(node_id),
            name=name,
            provision_state=provision_state,
            power_state=power_state,
            resource_class=resource_class,
            is_available=self._is_available(node),
            properties=properties,
            created_at=created_at,
            updated_at=updated_at,
        )

    def _parse_datetime(self, value: object) -> datetime:
        """Parse datetime fields from Ironic node data."""
        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(tzinfo=timezone.utc)
            return value
        if isinstance(value, str):
            try:
                parsed = datetime.fromisoformat(value)
                if parsed.tzinfo is None:
                    return parsed.replace(tzinfo=timezone.utc)
                return parsed
            except ValueError:
                return datetime.now(timezone.utc)
        return datetime.now(timezone.utc)
