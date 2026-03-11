"""Entrypoint executavel para o servidor MCP."""

from app.mcp.server import mcp


def main() -> None:
    """Executa o servidor MCP no transporte padrao."""
    mcp.run()


if __name__ == "__main__":
    main()
