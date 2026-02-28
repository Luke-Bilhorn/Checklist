from __future__ import annotations

from pathlib import Path

from lxml import etree

from .models import Checklist, ChecklistItem, ChecklistState, DEFAULT_STATES, _short_id

_OLD_ID_TO_NUMBER = {"todo": 0, "done": 1, "waiting": 2, "cancelled": 4}
_OLD_ID_TO_SYMBOL = {"todo": "empty", "done": "check", "waiting": "clock", "cancelled": "square"}


def _items_to_xml(parent: etree._Element, items: list[ChecklistItem]) -> None:
    for item in items:
        attrs: dict[str, str] = {
            "id": item.id,
            "text": item.text,
            "state": str(item.state_number),
        }
        if item.collapsed:
            attrs["collapsed"] = "true"
        el = etree.SubElement(parent, "item", **attrs)
        if item.children:
            _items_to_xml(el, item.children)


def _items_from_xml(parent: etree._Element) -> list[ChecklistItem]:
    items: list[ChecklistItem] = []
    for el in parent.findall("item"):
        raw_state = el.get("state", "0")
        try:
            state_num = int(raw_state)
        except ValueError:
            state_num = _OLD_ID_TO_NUMBER.get(raw_state, 0)
        items.append(
            ChecklistItem(
                id=el.get("id", _short_id()),
                text=el.get("text", ""),
                state_number=state_num,
                collapsed=el.get("collapsed", "false") == "true",
                children=_items_from_xml(el),
            )
        )
    return items


def save_checklist(checklist: Checklist, path: Path) -> None:
    root = etree.Element("checklist", name=checklist.name,
                         default_state=str(checklist.default_state_number))
    states_el = etree.SubElement(root, "states")
    for s in checklist.states:
        attrs = {
            "number": str(s.number), "label": s.label,
            "color": s.color, "symbol": s.symbol,
        }
        if not s.in_cycle:
            attrs["in_cycle"] = "false"
        etree.SubElement(states_el, "state", **attrs)
    items_el = etree.SubElement(root, "items")
    _items_to_xml(items_el, checklist.items)
    tree = etree.ElementTree(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(str(path), pretty_print=True, xml_declaration=True, encoding="UTF-8")


def load_checklist(path: Path) -> Checklist:
    tree = etree.parse(str(path))
    root = tree.getroot()
    name = root.get("name", "Untitled")

    states: list[ChecklistState] = []
    states_el = root.find("states")
    if states_el is not None:
        for s_el in states_el.findall("state"):
            num_attr = s_el.get("number")
            if num_attr is not None:
                states.append(
                    ChecklistState(
                        number=int(num_attr),
                        label=s_el.get("label", ""),
                        color=s_el.get("color", "#888888"),
                        symbol=s_el.get("symbol", "square"),
                        in_cycle=s_el.get("in_cycle", "true") != "false",
                    )
                )
            else:
                old_id = s_el.get("id", "")
                states.append(
                    ChecklistState(
                        number=_OLD_ID_TO_NUMBER.get(old_id, len(states)),
                        label=s_el.get("label", old_id.title()),
                        color=s_el.get("color", "#888888"),
                        symbol=_OLD_ID_TO_SYMBOL.get(old_id, "square"),
                    )
                )

    if not states:
        states = [
            ChecklistState(s.number, s.label, s.color, s.symbol)
            for s in DEFAULT_STATES
        ]

    items_el = root.find("items")
    items = _items_from_xml(items_el) if items_el is not None else []
    try:
        default_state = int(root.get("default_state", "0"))
    except ValueError:
        default_state = 0
    return Checklist(name=name, states=states, items=items,
                     default_state_number=default_state)


def list_checklists(data_dir: Path) -> list[Path]:
    data_dir.mkdir(parents=True, exist_ok=True)
    return sorted(data_dir.glob("*.xml"))
