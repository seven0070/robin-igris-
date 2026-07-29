"""PAM memory graph on eMMC — SQLite + FTS5 + typed edges. Knowledge lives here, not in weights."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

EdgeType = Literal["semantic", "causal", "temporal", "capital_of", "is_a", "part_of", "named", "episode"]


@dataclass
class Proposition:
    id: str
    subject: str
    relation: str
    obj: str
    confidence: float
    kind: str  # semantic | episodic | procedural | identity | causal
    text: str
    ts: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "subject": self.subject,
            "relation": self.relation,
            "object": self.obj,
            "confidence": self.confidence,
            "kind": self.kind,
            "text": self.text,
            "ts": self.ts,
        }


class GraphStore:
    """Unbounded knowledge on fast local storage (~500M propositions capacity class)."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.path))
        self._conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        c = self._conn
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS nodes (
                name TEXT PRIMARY KEY,
                strength REAL DEFAULT 1.0,
                hits INTEGER DEFAULT 0,
                last_used REAL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS edges (
                id TEXT PRIMARY KEY,
                src TEXT NOT NULL,
                dst TEXT NOT NULL,
                etype TEXT NOT NULL,
                weight REAL DEFAULT 0.1,
                hits INTEGER DEFAULT 0,
                last_used REAL DEFAULT 0,
                UNIQUE(src, dst, etype)
            );
            CREATE TABLE IF NOT EXISTS propositions (
                id TEXT PRIMARY KEY,
                subject TEXT,
                relation TEXT,
                object TEXT,
                confidence REAL,
                kind TEXT,
                text TEXT,
                ts REAL
            );
            CREATE VIRTUAL TABLE IF NOT EXISTS prop_fts USING fts5(
                text, subject, relation, object, content='propositions', content_rowid='rowid'
            );
            CREATE TRIGGER IF NOT EXISTS prop_ai AFTER INSERT ON propositions BEGIN
                INSERT INTO prop_fts(rowid, text, subject, relation, object)
                VALUES (new.rowid, new.text, new.subject, new.relation, new.object);
            END;
            CREATE TABLE IF NOT EXISTS meta (
                key TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )
        # Backfill FTS if empty but propositions exist (migration safety)
        n_fts = c.execute("SELECT count(*) FROM prop_fts").fetchone()[0]
        n_prop = c.execute("SELECT count(*) FROM propositions").fetchone()[0]
        if n_prop and not n_fts:
            c.execute("INSERT INTO prop_fts(prop_fts) VALUES('rebuild')")
        c.commit()

    def close(self) -> None:
        self._conn.close()

    def ensure_node(self, name: str) -> None:
        name = name.lower().strip()
        if not name:
            return
        self._conn.execute(
            """
            INSERT INTO nodes(name, last_used) VALUES(?, ?)
            ON CONFLICT(name) DO UPDATE SET hits = hits + 1, last_used = excluded.last_used,
                strength = MIN(10.0, strength + 0.01)
            """,
            (name, time.time()),
        )
        self._conn.commit()

    def link(
        self,
        src: str,
        dst: str,
        etype: str = "semantic",
        *,
        delta: float = 0.08,
    ) -> None:
        src, dst = src.lower().strip(), dst.lower().strip()
        if not src or not dst or src == dst:
            return
        self.ensure_node(src)
        self.ensure_node(dst)
        eid = f"{src}|{etype}|{dst}"
        now = time.time()
        self._conn.execute(
            """
            INSERT INTO edges(id, src, dst, etype, weight, hits, last_used)
            VALUES(?, ?, ?, ?, ?, 1, ?)
            ON CONFLICT(src, dst, etype) DO UPDATE SET
                weight = MIN(5.0, weight + excluded.weight),
                hits = hits + 1,
                last_used = excluded.last_used
            """,
            (eid, src, dst, etype, delta, now),
        )
        self._conn.commit()

    def add_proposition(
        self,
        *,
        subject: str,
        relation: str,
        obj: str,
        text: str,
        kind: str = "semantic",
        confidence: float = 0.9,
    ) -> Proposition:
        prop = Proposition(
            id=str(uuid.uuid4()),
            subject=subject.lower().strip(),
            relation=relation.lower().strip(),
            obj=obj.lower().strip(),
            confidence=confidence,
            kind=kind,
            text=text.strip(),
            ts=time.time(),
        )
        self._conn.execute(
            """
            INSERT INTO propositions(id, subject, relation, object, confidence, kind, text, ts)
            VALUES(?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                prop.id,
                prop.subject,
                prop.relation,
                prop.obj,
                prop.confidence,
                prop.kind,
                prop.text,
                prop.ts,
            ),
        )
        self.link(prop.subject, prop.obj, prop.relation if prop.relation else "semantic")
        self._conn.commit()
        return prop

    def search_fts(self, query: str, limit: int = 8) -> list[Proposition]:
        q = " ".join(t for t in query.replace('"', " ").split() if len(t) > 1)
        if not q:
            return []
        # FTS5 simple query
        try:
            rows = self._conn.execute(
                """
                SELECT p.* FROM prop_fts f
                JOIN propositions p ON p.rowid = f.rowid
                WHERE prop_fts MATCH ?
                ORDER BY rank
                LIMIT ?
                """,
                (q, limit),
            ).fetchall()
        except sqlite3.OperationalError:
            # fallback LIKE
            like = f"%{query[:40]}%"
            rows = self._conn.execute(
                "SELECT * FROM propositions WHERE text LIKE ? LIMIT ?",
                (like, limit),
            ).fetchall()
        return [self._row_prop(r) for r in rows]

    def traverse(
        self,
        start: str,
        *,
        relation: str | None = None,
        depth: int = 2,
        limit: int = 12,
    ) -> list[dict[str, Any]]:
        """BFS along typed edges — the engine's native operation."""
        start = start.lower().strip()
        seen = {start}
        frontier = [start]
        found: list[dict[str, Any]] = []
        for _ in range(max(1, depth)):
            nxt: list[str] = []
            for node in frontier:
                if relation:
                    rows = self._conn.execute(
                        """
                        SELECT * FROM edges WHERE src = ? AND etype = ?
                        ORDER BY weight DESC LIMIT ?
                        """,
                        (node, relation.lower(), limit),
                    ).fetchall()
                else:
                    rows = self._conn.execute(
                        """
                        SELECT * FROM edges WHERE src = ?
                        ORDER BY weight DESC LIMIT ?
                        """,
                        (node, limit),
                    ).fetchall()
                for r in rows:
                    dst = r["dst"]
                    found.append(
                        {
                            "src": r["src"],
                            "dst": dst,
                            "etype": r["etype"],
                            "weight": r["weight"],
                        }
                    )
                    self._conn.execute(
                        "UPDATE edges SET hits = hits + 1, last_used = ? WHERE id = ?",
                        (time.time(), r["id"]),
                    )
                    if dst not in seen:
                        seen.add(dst)
                        nxt.append(dst)
            frontier = nxt
            if not frontier:
                break
        self._conn.commit()
        return found[:limit]

    def find_relation(self, subject: str, relation: str) -> Proposition | None:
        subject, relation = subject.lower().strip(), relation.lower().strip()
        row = self._conn.execute(
            """
            SELECT * FROM propositions
            WHERE subject = ? AND relation = ?
            ORDER BY confidence DESC, ts DESC LIMIT 1
            """,
            (subject, relation),
        ).fetchone()
        if row:
            return self._row_prop(row)
        # edge fallback
        edges = self.traverse(subject, relation=relation, depth=1, limit=1)
        if edges:
            e = edges[0]
            return Proposition(
                id="edge:" + e["src"] + e["etype"] + e["dst"],
                subject=e["src"],
                relation=e["etype"],
                obj=e["dst"],
                confidence=min(0.95, float(e["weight"]) / 3.0),
                kind="semantic",
                text=f"{e['src']} --{e['etype']}--> {e['dst']}",
                ts=time.time(),
            )
        return None

    def hebbian_coactivate(self, concepts: list[str], delta: float = 0.05) -> None:
        concepts = [c.lower().strip() for c in concepts if c]
        for i, a in enumerate(concepts):
            self.ensure_node(a)
            for b in concepts[i + 1 :]:
                self.link(a, b, "semantic", delta=delta)
                self.link(b, a, "semantic", delta=delta * 0.5)

    def prune(self, min_weight: float = 0.05, max_age_days: float = 90.0) -> int:
        cutoff = time.time() - max_age_days * 86400
        cur = self._conn.execute(
            """
            DELETE FROM edges
            WHERE weight < ? AND hits < 3 AND last_used < ?
            """,
            (min_weight, cutoff),
        )
        self._conn.commit()
        return cur.rowcount

    def counts(self) -> dict[str, int]:
        return {
            "nodes": self._conn.execute("SELECT count(*) FROM nodes").fetchone()[0],
            "edges": self._conn.execute("SELECT count(*) FROM edges").fetchone()[0],
            "propositions": self._conn.execute("SELECT count(*) FROM propositions").fetchone()[0],
        }

    def set_meta(self, key: str, value: Any) -> None:
        self._conn.execute(
            "INSERT INTO meta(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, json.dumps(value)),
        )
        self._conn.commit()

    def get_meta(self, key: str, default: Any = None) -> Any:
        row = self._conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
        if not row:
            return default
        try:
            return json.loads(row["value"])
        except Exception:
            return row["value"]

    @staticmethod
    def _row_prop(r: sqlite3.Row) -> Proposition:
        return Proposition(
            id=r["id"],
            subject=r["subject"],
            relation=r["relation"],
            obj=r["object"],
            confidence=float(r["confidence"]),
            kind=r["kind"],
            text=r["text"],
            ts=float(r["ts"]),
        )
