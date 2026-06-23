"""Load the schema reference doc that grounds every agent prompt."""
from pathlib import Path

DEFAULT_SCHEMA_PATH = Path("schema_docs/schema.md")


def load_schema(path: Path | str = DEFAULT_SCHEMA_PATH) -> str:
    """Read the schema markdown that gets injected into agent prompts."""
    return Path(path).read_text()
