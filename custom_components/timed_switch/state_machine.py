# --------------------------------------------------------------------------------------------------
# File          : custom_components/timed_switch/state_machine.py
#
# Generikus, tábla-vezérelt állapotgép-motor (SPEC.md A2/5, CLAUDE.md 3.).
#
# Ez a fájl NEM tud semmit a Timed Switch konkrét állapotairól/eseményeiről — azt a
# transition_table.py adja meg adatként. Ide semmilyen if/elif állapotlogika nem kerülhet.
# --------------------------------------------------------------------------------------------------
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

_LOGGER = logging.getLogger(__name__)

Guard = Callable[[Any], bool]
Action = Callable[[Any], Awaitable[None]]


@dataclass(frozen=True)
class Transition:
    """Egy (állapot, esemény) cellán belüli egy lehetséges ág.

    `guard=None` azt jelenti: mindig illeszkedik (ez legyen mindig az utolsó a listában,
    mint "egyébként" ág). A cellák listaként vannak tárolva, hogy egy cellán belül több,
    guard-dal elágazó célállapot is elférjen (pl. SPEC.md B3.A MANUAL/schedule_on cella:
    manual_timeout==0 esetén AUTO, egyébként marad MANUAL).
    """

    target: str
    actions: tuple[Action, ...] = field(default_factory=tuple)
    guard: Optional[Guard] = None
    label: str = ""


# egy állapot összes eseményének cellái: esemény -> [Transition, ...]
StateCells = dict[str, list[Transition]]
# a teljes átmeneti tábla: állapot -> StateCells
TransitionTable = dict[str, StateCells]
# entry/exit akciók állapotonként
StateActions = dict[str, tuple[Action, ...]]


class StateMachine:
    """Generikus, tábla-vezérelt állapotgép.

    A tábla maga adja meg a teljes viselkedést (SPEC.md B3.A/B3.B + B3.1) — a motor csak
    a diszpécselést és az entry/exit szekvenálást végzi, döntést sosem hoz saját maga.
    """

    def __init__(
        self,
        name: str,
        table: TransitionTable,
        initial_state: str,
        entry_actions: Optional[StateActions] = None,
        exit_actions: Optional[StateActions] = None,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.name = name
        self.table = table
        self.state = initial_state
        self.entry_actions = entry_actions or {}
        self.exit_actions = exit_actions or {}
        self._log = logger or _LOGGER

    async def handle(self, event: str, ctx: Any) -> None:
        """Egy esemény feldolgozása. `ctx` a Controller (vagy teszt-kontextus), amit a
        guardok és az akciók kapnak paraméterül.

        CLAUDE.md 3.: ismeretlen (állapot, esemény) pár esetén csak figyelmeztető log,
        nincs kivétel, nincs állapotváltás.
        """
        old_state = self.state
        cell = self.table.get(old_state, {}).get(event)
        if cell is None:
            self._log.warning(
                "%s: ismeretlen (állapot=%s, esemény=%s) pár, figyelmen kívül hagyva",
                self.name, old_state, event,
            )
            return

        for transition in cell:
            if transition.guard is None or transition.guard(ctx):
                await self._execute(old_state, event, transition, ctx)
                return

        # Elvileg nem fordulhat elő, ha minden cella utolsó ága guard=None (lásd A2/1:
        # "üres cella = garantált hiba") — de védekezünk ellene, ahelyett hogy elszállna.
        self._log.warning(
            "%s: egyetlen guard sem illeszkedett (állapot=%s, esemény=%s) — hiányos tábla-cella",
            self.name, old_state, event,
        )

    async def _execute(self, old_state: str, event: str, transition: Transition, ctx: Any) -> None:
        for action in transition.actions:
            await action(ctx)

        if transition.target == old_state:
            self._log.debug(
                "%s: %s --%s--> (marad %s)%s",
                self.name, old_state, event, transition.target,
                f" [{transition.label}]" if transition.label else "",
            )
            return

        for action in self.exit_actions.get(old_state, ()):
            await action(ctx)

        self.state = transition.target

        for action in self.entry_actions.get(transition.target, ()):
            await action(ctx)

        self._log.info(
            "%s: %s --%s--> %s%s",
            self.name, old_state, event, transition.target,
            f" [{transition.label}]" if transition.label else "",
        )
# --------------------------------------------------------------------------------------------------
# EOF
# --------------------------------------------------------------------------------------------------
