"""Compatibility entrypoint; icon tooling lives in tools/convert_png_to_ico.py."""
from tools.convert_png_to_ico import convert_png_to_ico, main

__all__ = ["convert_png_to_ico", "main"]


if __name__ == "__main__":
    main()
