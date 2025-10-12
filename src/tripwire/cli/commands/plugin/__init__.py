"""Plugin command group for TripWire CLI.

This module provides plugin management commands for discovering, installing,
and managing TripWire plugins from the official registry.
"""

import click

from tripwire.cli.commands.plugin import install, ls, remove, search, update


@click.group(name="plugin")
def plugin() -> None:
    """Plugin management: install, search, update, and manage plugins.

    The plugin command group provides tools for extending TripWire with
    community plugins and custom environment variable sources:

    \b
    Commands:
      install  - Install a plugin from the registry
      search   - Search for plugins in the registry
      list     - List installed plugins
      update   - Update an installed plugin
      remove   - Remove an installed plugin

    \b
    Use Cases:
      - Install plugin: tripwire plugin install vault
      - Search plugins: tripwire plugin search aws
      - List installed: tripwire plugin list
      - Update plugin: tripwire plugin update vault --version 0.2.0
      - Remove plugin: tripwire plugin remove vault

    \b
    Example Plugins:
      - vault           - HashiCorp Vault integration
      - aws-secrets     - AWS Secrets Manager
      - azure-keyvault  - Azure Key Vault
      - remote-config   - Generic HTTP endpoint

    \b
    Registry:
      The official plugin registry is hosted on GitHub:
      https://github.com/tripwire-plugins/registry
    """
    pass


# Add subcommands to the group
plugin.add_command(install.install)
plugin.add_command(search.search)
plugin.add_command(ls.list_plugins)
plugin.add_command(update.update)
plugin.add_command(remove.remove)

__all__ = ["plugin"]
