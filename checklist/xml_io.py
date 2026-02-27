from __future__ import annotations

from pathlib import Path

from lxml import etree

from .models import Checklist, ChecklistItem, ChecklistState, DEFAULT_STATES, _short_id


def _items_to_xml(parent: etree._Element, items: list[ChecklistItem]) -> None:
    for item in items:
        el = etree.SubElement(parent, "item", id=item.id, text=item.text, state=item.state_id)
        if item.children:
            _items_to_xml(el, item.children)


def _items_from_xml(parent: etree._Element) -> list[ChecklistItem]:
    items: list[ChecklistItem] = []
    for el in parent.findall("item"):
        item = ChecklistItem(
            id=el.get("id", _short_id()),
            text=el.get("text", ""),
            state_id=el.get("state", "todo"),
            children=_items_from_xml(el),
        )
        items.append(item)
    return items


def save_checklist(checklist: Checklist, path: Path) -> None:
    root = etree.Element("checklist", name=checklist.name)

    states_el = etree.SubElement(root, "states")
    for s in checklist.states:
        etree.SubElement(states_el, "state", id=s.id, label=s.label, color=s.color)

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
            states.append(
                ChecklistState(
                    id=s_el.get("id", _short_id()),
                    label=s_el.get("label", ""),
                    color=s_el.get("color", "#888888"),
                )
            )
    if not states:
        states = list(DEFAULT_STATES)

    items_el = root.find("items")
    items = _items_from_xml(items_el) if items_el is not None else []

    return Checklist(name=name, states=states, items=items)


def list_checklists(data_dir: Path) -> list[Path]:
    data_dir.mkdir(parents=True, exist_ok=True)
    return sorted(data_dir.glob("*.xml"))
