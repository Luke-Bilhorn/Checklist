from __future__ import annotations

import uuid
from dataclasses import dataclass, field


def _short_id() -> str:
    return uuid.uuid4().hex[:8]


@dataclass
class ChecklistState:
    id: str
    label: str
    color: str  # hex, e.g. "#4CAF50"


@dataclass
class ChecklistItem:
    id: str = field(default_factory=_short_id)
    text: str = ""
    state_id: str = "todo"
    children: list[ChecklistItem] = field(default_factory=list)


DEFAULT_STATES: list[ChecklistState] = [
    ChecklistState(id="done", label="Done", color="#4CAF50"),
    ChecklistState(id="todo", label="To Do", color="#F44336"),
    ChecklistState(id="waiting", label="Waiting", color="#9C27B0"),
    ChecklistState(id="cancelled", label="Cancelled", color="#9E9E9E"),
]


@dataclass
class Checklist:
    name: str = "Untitled"
    states: list[ChecklistState] = field(default_factory=lambda: [s for s in DEFAULT_STATES])
    items: list[ChecklistItem] = field(default_factory=list)

    def state_by_id(self, state_id: str) -> ChecklistState | None:
        for s in self.states:
            if s.id == state_id:
                return s
        return None

    def next_state(self, current_id: str) -> ChecklistState:
        ids = [s.id for s in self.states]
        try:
            idx = ids.index(current_id)
        except ValueError:
            idx = -1
        return self.states[(idx + 1) % len(self.states)]
