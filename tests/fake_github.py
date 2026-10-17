"""In-memory stand-in for GitHub, for `coding.issues.set_github()`.

The counterpart of `fake_drive.py` for issues: it remembers what was filed, so
a test can check that a second run comments on the open issue instead of
filing a duplicate, and `calls` records every request in order.
"""
from __future__ import annotations

from typing import Dict, List, Optional


class FakeGitHub:
    def __init__(self, signed_in: bool = True, first_number: int = 900):
        self.signed_in = signed_in
        self.issues: List[Dict] = []        # every issue ever filed; numbers never reused
        self.comments: Dict[int, List[str]] = {}
        self.labels: List[Dict] = []
        self.calls: List[tuple] = []
        self._next = first_number

    # --- helpers for tests -------------------------------------------------

    def seed_issue(self, title: str, label: str, body: str = "", state: str = "OPEN",
                   created_at: str = "2026-01-01T00:00:00Z",
                   closed_at: Optional[str] = None) -> int:
        number = self._next
        self._next += 1
        self.issues.append({"number": number, "title": title, "labels": [label],
                            "state": state, "body": body, "createdAt": created_at,
                            "closedAt": closed_at})
        return number

    def issue(self, number: int) -> Optional[Dict]:
        return next((i for i in self.issues if i["number"] == number), None)

    def calls_of(self, kind: str) -> List[tuple]:
        return [c for c in self.calls if c[0] == kind]

    # --- the GitHub protocol -----------------------------------------------

    def available(self) -> bool:
        return self.signed_in

    def list_issues(self, label: str, state: str = "open") -> List[Dict]:
        self.calls.append(("list", label, state))
        return [dict(i) for i in self.issues
                if label in i["labels"] and (state == "all" or i["state"] == state.upper())]

    def get_issue(self, number: int) -> Optional[Dict]:
        self.calls.append(("view", number))
        issue = self.issue(number)
        return dict(issue) if issue else None

    def create_issue(self, title: str, label: str, body: str) -> int:
        # Like GitHub: an issue can't be filed under a label the repository lacks.
        if label not in {l["name"] for l in self.labels}:
            raise RuntimeError(f"`gh issue create` failed: could not add label: "
                               f"'{label}' not found")
        number = self.seed_issue(title, label, body,
                                 created_at="2026-10-13T00:00:00Z")
        self.calls.append(("create", number, title, label, body))
        return number

    def edit_issue(self, number: int, title: Optional[str], body: Optional[str]) -> None:
        self.calls.append(("edit", number, title, body))
        issue = self.issue(number)
        if title is not None:
            issue["title"] = title
        if body is not None:
            issue["body"] = body

    def comment(self, number: int, body: str) -> None:
        self.calls.append(("comment", number, body))
        self.comments.setdefault(number, []).append(body)

    def close_issue(self, number: int) -> None:
        self.calls.append(("close", number))
        self.issue(number).update(state="CLOSED", closedAt="2026-10-13T00:00:00Z")

    def list_labels(self) -> List[Dict]:
        return [dict(l) for l in self.labels]

    def create_label(self, name: str, color: str, description: str) -> None:
        self.calls.append(("create_label", name))
        self.labels.append({"name": name, "color": color, "description": description})

    def edit_label(self, name: str, color: str, description: str) -> None:
        self.calls.append(("edit_label", name))
        for l in self.labels:
            if l["name"] == name:
                l.update(color=color, description=description)

    def delete_label(self, name: str) -> None:
        self.calls.append(("delete_label", name))
        self.labels = [l for l in self.labels if l["name"] != name]
