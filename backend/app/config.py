import os
from functools import lru_cache
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
RULES_PATH = Path(__file__).parent / "rules" / "ekatra_rules.yaml"
DATABASE_URL = os.environ.get("DATABASE_URL", f"sqlite:///{(ROOT / 'data' / 'ekatra.db').as_posix()}")
EVAL_RESULTS = ROOT / "eval" / "results.json"
USE_E5 = os.environ.get("USE_E5", "auto")  # auto | on | off

REGIONS = ["North", "South", "East", "West", "Central", "North-East"]
CATEGORIES = ["Infrastructure", "Faculty", "Fees & refund", "Ragging", "Norms violation", "Admission", "Other"]
STATUSES = ["Received", "Under process", "Pending", "Transferred", "Disposed", "Beyond timeline"]
SEVERITIES = ["CONFLICTING", "DUPLICATE", "RELATED", "INFO"]


@lru_cache
def rules() -> dict:
    return yaml.safe_load(RULES_PATH.read_text(encoding="utf8"))
