"""Configuration: dotenv loading, startup validation, shop hours and the clock.

NFR-1: secrets come from a gitignored .env and a missing key fails at startup with ONE
readable sentence. FR-1 level 1: the process default model is read from the environment.
FR-4: shop hours and an optional simulated clock come from here.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

REQUIRED_KEYS = ("OPENAI_API_KEY",)

MISSING_KEY_SENTENCE = (
    "Shop Desk cannot start: {keys} is not set. Copy .env.example to .env and add your key."
)


class ConfigError(RuntimeError):
    """A startup problem the operator can fix. Always carries one readable sentence."""


@dataclass(frozen=True)
class Settings:
    openai_api_key: str
    default_model: str | None
    open_hour: int
    close_hour: int
    simulated_hour: int | None
    turn_ceiling: int
    catalogue_path: Path
    base_dir: Path

    def is_open_at(self, hour: int) -> bool:
        """True when the shop is open at the given hour (FR-4)."""
        if self.open_hour <= self.close_hour:
            return self.open_hour <= hour < self.close_hour
        return hour >= self.open_hour or hour < self.close_hour

    def current_hour(self) -> int:
        """The hour the Desk should reason about — simulated when configured (FR-4)."""
        if self.simulated_hour is not None:
            return self.simulated_hour
        return datetime.now().hour


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:  # bad configuration still must not crash with a traceback
        raise ConfigError(
            f"Shop Desk cannot start: {name} must be a whole number, but it is {raw!r}."
        ) from exc


def load_settings(load_env_file: bool = True) -> Settings:
    """Load configuration. Raises ConfigError carrying exactly one sentence (NFR-1)."""
    if load_env_file:
        load_dotenv()

    missing = [key for key in REQUIRED_KEYS if not os.getenv(key)]
    if missing:
        raise ConfigError(MISSING_KEY_SENTENCE.format(keys=" and ".join(missing)))

    base_dir = Path(__file__).resolve().parent.parent
    catalogue = Path(os.getenv("CATALOGUE_PATH", "catalogue.json"))
    if not catalogue.is_absolute():
        catalogue = base_dir / catalogue

    simulated_raw = os.getenv("SHOP_SIMULATED_HOUR")
    simulated_hour = None
    if simulated_raw is not None and simulated_raw.strip() != "":
        simulated_hour = _int_env("SHOP_SIMULATED_HOUR", 0)

    return Settings(
        openai_api_key=os.environ["OPENAI_API_KEY"],
        default_model=os.getenv("OPENAI_DEFAULT_MODEL") or None,
        open_hour=_int_env("SHOP_OPEN_HOUR", 10),
        close_hour=_int_env("SHOP_CLOSE_HOUR", 20),
        simulated_hour=simulated_hour,
        turn_ceiling=_int_env("TURN_CEILING", 10),
        catalogue_path=catalogue,
        base_dir=base_dir,
    )
