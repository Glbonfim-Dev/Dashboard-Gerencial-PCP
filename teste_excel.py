"""Atalho legado para testar a automacao sem publicar no GitHub."""

from __future__ import annotations

import sys

from publicar_dashboard import main


if __name__ == "__main__":
    # Reaproveita o fluxo real, mas impede qualquer envio durante o teste manual.
    raise SystemExit(main([*sys.argv[1:], "--no-upload"]))
