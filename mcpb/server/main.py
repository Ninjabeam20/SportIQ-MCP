"""MCPB entry-point launcher for SportIQ.

Claude Desktop launches this extension via `mcp_config` (`uvx sportiq-mcp`), which
pulls the published package from PyPI into an ephemeral environment. This file is a
functional fallback: if the entry point is invoked directly, it shells out to the same
`uvx` command. Requires the `uv` toolchain on the host (https://docs.astral.sh/uv/).
"""

import shutil
import subprocess
import sys


def main() -> int:
    if shutil.which("uvx") is None:
        sys.stderr.write(
            "SportIQ requires the `uv` toolchain (uvx). Install it from "
            "https://docs.astral.sh/uv/ and restart.\n"
        )
        return 1
    return subprocess.call(["uvx", "sportiq-mcp", *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())
