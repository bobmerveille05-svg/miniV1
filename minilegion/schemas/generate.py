"""Generate JSON Schema files from Pydantic models.

Writes all 6 artifact schemas to minilegion/schemas/{name}.schema.json.
Runnable as: python -m minilegion.schemas.generate

Output is deterministic — running again produces identical files.
"""

import json
from pathlib import Path

from minilegion.core.registry import SCHEMA_REGISTRY


def generate_all() -> list[Path]:
    """Generate JSON Schema files for all registered schemas.

    Returns:
        List of paths to generated schema files.
    """
    output_dir = Path(__file__).parent
    generated: list[Path] = []

    for name, model_cls in sorted(SCHEMA_REGISTRY.items()):
        schema = model_cls.model_json_schema()
        path = output_dir / f"{name}.schema.json"
        path.write_text(json.dumps(schema, indent=2) + "\n", encoding="utf-8")
        generated.append(path)

    return generated


if __name__ == "__main__":
    paths = generate_all()
    for p in paths:
        print(f"Generated: {p}")
