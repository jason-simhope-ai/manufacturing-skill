"""Integrations that cross the process/network boundary.

Not covered by the core's no-subprocess/no-network invariant (that applies to `chat_gateway`
only). Loaded lazily by name (see `chat_gateway.drivers.load_driver_class`); never imported by
the `chat_gateway` core at module import time.
"""
