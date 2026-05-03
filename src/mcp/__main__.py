"""FastMCP server entry point."""
import sys

from src.mcp.server import mcp

if __name__ == "__main__":
    mcp.run()