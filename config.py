"""
Amazon SP-API model selection.

Set SP_API_MODELS env var to a comma-separated list of model directory names
to load only specific APIs. Leave empty/unset to load all models.

Common subsets:
  core    = orders, catalog, listings, inventory, pricing, reports, finances
  vendor  = vendor-orders, vendor-shipments, vendor-invoices, vendor-direct-fulfillment-*
"""

import os
import re
from pathlib import Path

MODELS_DIR = Path("/app/sp-api-models/models")

CORE_MODELS = [
    "orders-api-model",
    "catalog-items-api-model",
    "listings-items-api-model",
    "fba-inventory-api-model",
    "product-pricing-api-model",
    "reports-api-model",
    "feeds-api-model",
    "finances-api-model",
    "notifications-api-model",
    "sellers-api-model",
    "product-fees-api-model",
    "sales-api-model",
]


def pick_latest_spec(model_dir: Path) -> Path | None:
    """Pick the latest spec file from a model directory.

    Prefers dated versions (e.g. orders_2026-01-01.json) over legacy (ordersV0.json).
    Falls back to whatever JSON file exists.
    """
    json_files = sorted(model_dir.glob("*.json"))
    if not json_files:
        return None

    dated = [f for f in json_files if re.search(r"\d{4}-\d{2}-\d{2}", f.name)]
    if dated:
        return dated[-1]  # latest date
    return json_files[-1]


def get_spec_files() -> list[str]:
    """Return list of spec file paths to load based on configuration."""
    selected = os.environ.get("SP_API_MODELS", "").strip()

    if selected.lower() == "all":
        model_dirs = sorted(MODELS_DIR.iterdir())
    elif selected:
        names = [n.strip() for n in selected.split(",") if n.strip()]
        model_dirs = [MODELS_DIR / n for n in names if (MODELS_DIR / n).is_dir()]
    else:
        # Default: core models
        model_dirs = [MODELS_DIR / n for n in CORE_MODELS if (MODELS_DIR / n).is_dir()]

    specs = []
    for d in model_dirs:
        if not d.is_dir():
            continue
        spec = pick_latest_spec(d)
        if spec:
            specs.append(str(spec))

    return specs
