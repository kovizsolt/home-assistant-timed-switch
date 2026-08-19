# --------------------------------------------------------------------------------------------------
# File          : custom_components/timed_switch/helpers.py
#
# Cron-kifejezés lista kiértékelése (SPEC.md B2.4: croniter szintaxis, perc-pontosság,
# soronként/vesszővel elválasztva, `#` a komment) és a Store-ban perzisztált adat alakja
# (SPEC.md B3.2).
# --------------------------------------------------------------------------------------------------
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from croniter import croniter


class CronFieldCountError(ValueError):
    """A cron expression has non-wildcard fields beyond the supported five."""


def normalize_cron_list(raw: str) -> str:
    """Complete short cron expressions and remove wildcard-only extra fields."""
    normalized_lines: list[str] = []
    for line in raw.splitlines():
        expression_text, separator, comment = line.partition("#")
        normalized_expressions: list[str] = []
        for chunk in expression_text.split(","):
            expression = chunk.strip()
            if not expression:
                continue
            fields = expression.split()
            if len(fields) < 5:
                fields.extend("*" for _ in range(5 - len(fields)))
            elif len(fields) > 5:
                if any(field != "*" for field in fields[5:]):
                    raise CronFieldCountError(expression)
                fields = fields[:5]
            normalized_expressions.append(" ".join(fields))

        normalized_line = ", ".join(normalized_expressions)
        if separator:
            normalized_line += (" " if normalized_line else "") + f"#{comment}"
        normalized_lines.append(normalized_line)
    return "\n".join(normalized_lines)


def parse_cron_list(raw: str) -> list[str]:
    """Cron-lista szöveges mezőből (soronként vagy vesszővel elválasztva, `#` komment)."""
    if not raw:
        return []
    parts: list[str] = []
    for line in raw.splitlines():
        line = re.split(r"#", line, maxsplit=1)[0]
        for chunk in line.split(","):
            chunk = chunk.strip()
            if chunk:
                parts.append(chunk)
    return parts


@dataclass
class ScheduleResult:
    """A cron-motor egy kiértékelésének eredménye (SPEC.md B2.4/B3.2)."""

    timed_state: Optional[bool]  # None = mindkét lista üres, nincs időzítés
    next_schedule: Optional[datetime]


def evaluate_schedule(
    on_crons: list[str], off_crons: list[str], now: datetime
) -> ScheduleResult:
    """SPEC.md: `timed_state` = amelyik lista (ON/OFF) utolsó múltbeli találata későbbi;
    ha mindkettő üres, nincs időzítés (None — a hívó a `default_state`-et használja).
    `next_schedule` = a legközelebbi jövőbeli találat bármelyik listából.
    """
    if not on_crons and not off_crons:
        return ScheduleResult(timed_state=None, next_schedule=None)

    last_on = _last_before(on_crons, now)
    last_off = _last_before(off_crons, now)

    if last_on is None and last_off is None:
        timed_state: Optional[bool] = None
    elif last_off is None:
        timed_state = True
    elif last_on is None:
        timed_state = False
    else:
        timed_state = last_on > last_off

    next_schedule = _next_after(on_crons + off_crons, now)
    return ScheduleResult(timed_state=timed_state, next_schedule=next_schedule)


def _last_before(exprs: list[str], now: datetime) -> Optional[datetime]:
    best: Optional[datetime] = None
    for expr in exprs:
        try:
            candidate = croniter(expr, now).get_prev(datetime)
        except Exception:  # rossz cron-kifejezés — kihagyjuk, nem dobunk kivételt
            continue
        if best is None or candidate > best:
            best = candidate
    return best


def _next_after(exprs: list[str], now: datetime) -> Optional[datetime]:
    best: Optional[datetime] = None
    for expr in exprs:
        try:
            candidate = croniter(expr, now).get_next(datetime)
        except Exception:
            continue
        if best is None or candidate < best:
            best = candidate
    return best


@dataclass
class PersistedState:
    """SPEC.md B3.2 — a Store-ban tárolt Controller-állapot. `timed_state` szándékosan
    NEM szerepel itt: sosem perzisztált, mindig frissen számolt (B3.2/#3)."""

    main_state: str  # AUTO / MANUAL
    expected_state: bool
    manual_until: Optional[str]  # ISO 8601, csak MANUAL + manual_timeout>0 esetén

    def to_dict(self) -> dict:
        return {
            "main_state": self.main_state,
            "expected_state": self.expected_state,
            "manual_until": self.manual_until,
        }

    @classmethod
    def from_dict(cls, raw: Optional[dict]) -> Optional["PersistedState"]:
        if not raw:
            return None
        try:
            return cls(
                main_state=raw["main_state"],
                expected_state=bool(raw["expected_state"]),
                manual_until=raw.get("manual_until"),
            )
        except (KeyError, TypeError, ValueError):
            return None
# --------------------------------------------------------------------------------------------------
# EOF
# --------------------------------------------------------------------------------------------------
