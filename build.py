#!/usr/bin/env python3
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

"""
Build automation script for containerizing the Ironic AIO API.

This script handles building and pushing Docker images. It uses only Python
built-in libraries and can be used locally or in CI/CD pipelines like GitHub Actions.

Usage:
    python build.py --help
    python build.py build
    python build.py build --tag latest
    python build.py build --push
    python build.py build --push --registry ghcr.io --repo mattcburns/ironic-aio-api
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional


class BuildConfig:
    """Configuration for container builds."""

    def __init__(
        self,
        registry: str = "docker.io",
        repo: str = "mattcburns/ironic-aio-api",
        tag: str = "latest",
        dockerfile: str = "Dockerfile",
        context: str = ".",
        push: bool = False,
    ):
        self.registry = registry
        self.repo = repo
        self.tag = tag
        self.dockerfile = dockerfile
        self.context = context
        self.push = push

    @property
    def image_name(self) -> str:
        """Return the full image name including registry."""
        return f"{self.registry}/{self.repo}:{self.tag}"

    @property
    def image_name_no_registry(self) -> str:
        """Return the image name without registry."""
        return f"{self.repo}:{self.tag}"


class ContainerBuilder:
    """Handles building and pushing Docker container images."""

    def __init__(self, config: BuildConfig):
        self.config = config
        self.project_root = Path(__file__).parent.absolute()

    def validate_environment(self) -> bool:
        """Validate that required tools and files exist."""
        # Check if docker is available
        result = subprocess.run(
            ["docker", "--version"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print("Error: Docker is not installed or not available in PATH")
            return False

        # Check if Dockerfile exists
        dockerfile_path = self.project_root / self.config.dockerfile
        if not dockerfile_path.exists():
            print(f"Error: Dockerfile not found at {dockerfile_path}")
            return False

        # Check if we can access the context
        context_path = self.project_root / self.config.context
        if not context_path.exists():
            print(f"Error: Build context not found at {context_path}")
            return False

        return True

    def build(self) -> bool:
        """Build the container image."""
        print(f"Building container image: {self.config.image_name_no_registry}")

        build_cmd = [
            "docker",
            "build",
            "-f",
            str(self.project_root / self.config.dockerfile),
            "-t",
            self.config.image_name_no_registry,
        ]

        # Add registry tag if registry is not docker.io (default)
        if self.config.registry != "docker.io":
            build_cmd.extend(["-t", self.config.image_name])

        build_cmd.append(str(self.project_root / self.config.context))

        print(f"Running: {' '.join(build_cmd)}")

        result = subprocess.run(build_cmd)
        if result.returncode != 0:
            print(f"Error: Failed to build container image")
            return False

        print(f"✓ Successfully built: {self.config.image_name_no_registry}")
        return True

    def push(self) -> bool:
        """Push the container image to registry."""
        if self.config.registry == "docker.io":
            image = self.config.image_name_no_registry
        else:
            image = self.config.image_name

        print(f"Pushing container image: {image}")

        push_cmd = ["docker", "push", image]

        print(f"Running: {' '.join(push_cmd)}")

        result = subprocess.run(push_cmd)
        if result.returncode != 0:
            print(f"Error: Failed to push container image")
            return False

        print(f"✓ Successfully pushed: {image}")
        return True

    def get_image_digest(self) -> Optional[str]:
        """Get the digest of the built image."""
        image = (
            self.config.image_name_no_registry
            if self.config.registry == "docker.io"
            else self.config.image_name
        )

        result = subprocess.run(
            ["docker", "inspect", "--format={{index .RepoDigests 0}}", image],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            digest = result.stdout.strip()
            if digest:
                return digest
        return None

    def save_metadata(self, output_file: str = "build-metadata.json") -> bool:
        """Save build metadata to a JSON file."""
        digest = self.get_image_digest()

        metadata = {
            "image": (
                self.config.image_name_no_registry
                if self.config.registry == "docker.io"
                else self.config.image_name
            ),
            "registry": self.config.registry,
            "repository": self.config.repo,
            "tag": self.config.tag,
            "digest": digest,
            "push": self.config.push,
        }

        output_path = self.project_root / output_file

        try:
            with open(output_path, "w") as f:
                json.dump(metadata, f, indent=2)
            print(f"✓ Saved build metadata to {output_file}")
            return True
        except Exception as e:
            print(f"Warning: Failed to save build metadata: {e}")
            return False

    def run(self) -> bool:
        """Execute the full build process."""
        if not self.validate_environment():
            return False

        if not self.build():
            return False

        if self.config.push:
            if not self.push():
                return False

        self.save_metadata()
        return True


def main():
    """Main entry point for the build script."""
    parser = argparse.ArgumentParser(
        description="Build and push the Ironic AIO API container image",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python build.py build
  python build.py build --tag v1.0.0
  python build.py build --push
  python build.py build --push --registry ghcr.io
  python build.py build --tag latest --push --registry ghcr.io
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    build_parser = subparsers.add_parser("build", help="Build container image")
    build_parser.add_argument(
        "--tag",
        default=os.getenv("DOCKER_TAG", "latest"),
        help="Docker image tag (default: latest or DOCKER_TAG env var)",
    )
    build_parser.add_argument(
        "--registry",
        default=os.getenv("DOCKER_REGISTRY", "docker.io"),
        help="Docker registry (default: docker.io or DOCKER_REGISTRY env var)",
    )
    build_parser.add_argument(
        "--repo",
        default=os.getenv("DOCKER_REPO", "mattcburns/ironic-aio-api"),
        help="Repository name (default: mattcburns/ironic-aio-api or DOCKER_REPO env var)",
    )
    build_parser.add_argument(
        "--push",
        action="store_true",
        help="Push image to registry after build",
    )
    build_parser.add_argument(
        "--dockerfile",
        default="Dockerfile",
        help="Path to Dockerfile (default: Dockerfile)",
    )
    build_parser.add_argument(
        "--context",
        default=".",
        help="Build context (default: .)",
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    if args.command == "build":
        config = BuildConfig(
            registry=args.registry,
            repo=args.repo,
            tag=args.tag,
            dockerfile=args.dockerfile,
            context=args.context,
            push=args.push,
        )

        builder = ContainerBuilder(config)
        success = builder.run()

        return 0 if success else 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
