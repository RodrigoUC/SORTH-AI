# Isolated MCP companion notices

This directory records all 38 verified Windows x64 CPython 3.12 wheels in
`project_root/requirements-mcp-windows.lock`: optional MCP 1.30.0, its transitive
runtime dependencies and isolated PyInstaller build tools. It excludes GUI,
model-provider and test dependencies. Wheel hashes were verified against the
existing reviewed optional and Windows locks before generating this lock.
`tools/lock_windows.py` also verifies Windows markers and requested extras.

Regenerate from a clean directory of every exact locked wheel:

    python tools/lock_windows.py --wheel-dir build/mcp/wheels --scope mcp --output requirements-mcp-windows.lock
    python tools/collect_license_notices.py --wheel-dir build/mcp/wheels --lock requirements-mcp-windows.lock --output ../third_party/mcp
    python tools/mcp_payload.py notices

The collector never installs or executes wheels; it fails on missing, duplicate,
unmatched or modified wheels and missing upstream notice files. The verifier
requires the exact inventory and original notice-byte hashes. New build output
must carry these notices plus SORTH's license and the reference CPython notice.

This is an inventory of the isolated build environment, not a binary SBOM or a
legal certification. Build tools may not ship in the companion. PyInstaller's
bootloader exception and upstream cryptography/Rust/Windows runtime notices
remain relevant; exact frozen native dependency and source review is still a
release gate. No network service, model, account or credential is included.
