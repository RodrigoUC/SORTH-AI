"""Regenerate the fully synthetic sample JSON and original icon assets.

The former institution-specific PDF extraction workflow has been retired.
"""
from tools.generate_demo_assets import generate

if __name__ == "__main__":
    generate()
    print("Datos de ejemplo sintéticos regenerados. Ver data/input/PROVENANCE.md.")
