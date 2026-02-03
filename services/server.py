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

from clients.ironic import IronicClient
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
        # TODO: Query Ironic nodes
        # nodes = await self.ironic.list_nodes()

        # TODO: Apply filters
        # if provision_state:
        #     nodes = [n for n in nodes if n.provision_state == provision_state]
        # if resource_class:
        #     nodes = [n for n in nodes if n.resource_class == resource_class]
        # if available_only:
        #     nodes = [n for n in nodes if self._is_available(n)]

        # Mock implementation for now
        all_servers = []

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
            ValueError: If server not found
        """
        # TODO: Fetch node from Ironic
        # node = await self.ironic.get_node(server_id)
        # if node is None:
        #     raise ValueError(f"Server '{server_id}' not found")

        # TODO: Transform node to ServerSummary
        # return self._node_to_summary(node)

        raise NotImplementedError("Ironic API call not implemented yet.")

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
        # TODO: Implement business logic
        # Available if: provision_state == 'available' and not in maintenance and power_state == 'power off'
        return False

    def _node_to_summary(self, node) -> ServerSummary:
        """
        Transform an Ironic node to ServerSummary.

        Args:
            node: Ironic node object

        Returns:
            ServerSummary with transformed data
        """
        # TODO: Transform node object to ServerSummary
        # This should extract relevant properties and compute is_available
        raise NotImplementedError("Ironic API call not implemented yet.")
