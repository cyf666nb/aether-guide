# SCORE-IMPACT: API contract delivery and OpenAPI 3.1 artifact generation.
from pathlib import Path

import yaml
from aether_api.main import app


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    target = root / "docs" / "api" / "openapi.yaml"
    openapi_yaml = yaml.safe_dump(app.openapi(), sort_keys=False, allow_unicode=True)
    target.write_text(openapi_yaml, encoding="utf-8")
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
