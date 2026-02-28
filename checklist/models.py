from __future__ import annotations

import uuid
from dataclasses import dataclass, field


def _short_id() -> str:
    return uuid.uuid4().hex[:8]


AVAILABLE_SYMBOLS = [
    ("bullet", "Small Bullet"),
    ("empty", "Empty Checkbox"),
    ("check", "Checkmark"),
    ("clock", "Clock"),
    ("minus", "Minus"),
    ("square", "Filled Square"),
    ("x", "X Mark"),
    ("star", "Star"),
    ("exclaim", "Exclamation"),
    ("question", "Question Mark"),
]


@dataclass
class ChecklistState:
    number: int
    label: str
    color: str
    symbol: str  # key from AVAILABLE_SYMBOLS
    in_cycle: bool = True  # whether this state is included in click-cycling


DEFAULT_STATES: list[ChecklistState] = [
    ChecklistState(number=-1, label="Bullet", color="#bbbbbb", symbol="bullet", in_cycle=False),
    ChecklistState(number=0, label="To Do", color="#F44336", symbol="empty"),
    ChecklistState(number=1, label="Done", color="#4CAF50", symbol="check"),
    ChecklistState(number=2, label="Waiting", color="#9C27B0", symbol="clock"),
    ChecklistState(number=3, label="On Hold", color="#FFC107", symbol="minus"),
    ChecklistState(number=4, label="Cancelled", color="#757575", symbol="x"),
]


@dataclass
class ChecklistItem:
    id: str = field(default_factory=_short_id)
    text: str = ""
    state_number: int = 0
    collapsed: bool = False
    children: list[ChecklistItem] = field(default_factory=list)


@dataclass
class Checklist:
    name: str = "Untitled"
    states: list[ChecklistState] = field(
        default_factory=lambda: [
            ChecklistState(s.number, s.label, s.color, s.symbol)
            for s in DEFAULT_STATES
        ]
    )
    items: list[ChecklistItem] = field(default_factory=list)
    default_state_number: int = 0

    def state_by_number(self, number: int) -> ChecklistState | None:
        for s in self.states:
            if s.number == number:
                return s
        return None

    def checkbox_states(self) -> list[ChecklistState]:
        return sorted(
            [s for s in self.states if s.number >= 0], key=lambda s: s.number
        )

    def cycleable_states(self) -> list[ChecklistState]:
        return sorted(
            [s for s in self.states if s.number >= 0 and s.in_cycle],
            key=lambda s: s.number,
        )

    def next_checkbox_state(self, current: int) -> ChecklistState:
        cb = self.cycleable_states()
        if not cb:
            cb = self.checkbox_states()
        if not cb:
            return self.states[0]
        nums = [s.number for s in cb]
        try:
            idx = nums.index(current)
            return cb[(idx + 1) % len(cb)]
        except ValueError:
            return cb[0]

    def smart_click_target(self, current: int) -> int:
        """First-click (or after 1s pause) target for a checkbox indicator."""
        if current == 1:
            st = self.state_by_number(0)
            return 0 if st else self.checkbox_states()[0].number
        st = self.state_by_number(1)
        return 1 if st else self.checkbox_states()[0].number
