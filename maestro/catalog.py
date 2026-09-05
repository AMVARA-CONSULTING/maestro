"""Load Maestro project catalog (existence index + context pack pointers)."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AutoagentsInfo:
    """Per-project autoagents (agents) install on the catalog host."""

    rel_dir: str
    loop: str

    def dir_path(self, project_path: Path) -> Path:
        return Path(project_path) / self.rel_dir

    def loop_path(self, project_path: Path) -> Path:
        return self.dir_path(project_path) / self.loop


@dataclass(frozen=True)
class ProjectEntry:
    id: str
    host: str
    kind: str
    path: Path
    summary: str
    context_rel: str
    aliases: tuple[str, ...]
    active: bool
    ssh_alias: str
    autoagents: AutoagentsInfo | None = None
    #: Hub / documentation Redmine issue for this catalog project (MaestroBot notes).
    redmine_doc_issue_id: int | None = None

    @property
    def label(self) -> str:
        return self.id

    def is_local_to(self, local_host: str) -> bool:
        return self.host.casefold() == local_host.strip().casefold()


@dataclass(frozen=True)
class HostCatalog:
    host: str
    description: str
    ssh_alias: str
    projects: tuple[ProjectEntry, ...]

    def active_projects(self) -> tuple[ProjectEntry, ...]:
        return tuple(p for p in self.projects if p.active)


@dataclass(frozen=True)
class CatalogIndex:
    """All host catalogs loaded from catalog/hosts/*.json."""

    local_host: str
    hosts: dict[str, HostCatalog]

    def list_hosts(self) -> tuple[str, ...]:
        return tuple(sorted(self.hosts))

    def get_host(self, host: str) -> HostCatalog | None:
        return self.hosts.get(host.strip().casefold())

    def all_active(self) -> tuple[ProjectEntry, ...]:
        out: list[ProjectEntry] = []
        for h in sorted(self.hosts):
            out.extend(self.hosts[h].active_projects())
        return tuple(out)

    def with_autoagents(self) -> tuple[ProjectEntry, ...]:
        return tuple(p for p in self.all_active() if p.autoagents is not None)

    def get(self, key: str) -> ProjectEntry | None:
        k = key.strip().casefold()
        if not k:
            return None
        # Prefer exact id match; if several hosts share alias, prefer local host.
        id_hits: list[ProjectEntry] = []
        alias_hits: list[ProjectEntry] = []
        for p in self.all_active():
            if p.id.casefold() == k:
                id_hits.append(p)
            for alias in p.aliases:
                if alias.casefold() == k:
                    alias_hits.append(p)
                    break
        for pool in (id_hits, alias_hits):
            if not pool:
                continue
            for p in pool:
                if p.is_local_to(self.local_host):
                    return p
            return pool[0]
        return None

    def resolve_from_text(self, text: str) -> ProjectEntry | None:
        """Best-effort match: longest id/alias; prefer local host on ties."""
        blob = (text or "").casefold()
        if not blob:
            return None
        candidates: list[tuple[int, int, ProjectEntry]] = []
        for p in self.all_active():
            names = (p.id, *p.aliases)
            for name in names:
                n = name.casefold().strip()
                if len(n) < 2:
                    continue
                if re.search(rf"(?<![\w-]){re.escape(n)}(?![\w-])", blob):
                    local_bonus = 1 if p.is_local_to(self.local_host) else 0
                    candidates.append((len(n), local_bonus, p))
        if not candidates:
            return None
        candidates.sort(key=lambda t: (t[0], t[1]), reverse=True)
        return candidates[0][2]


def _parse_autoagents(raw: object) -> AutoagentsInfo | None:
    if not isinstance(raw, dict):
        return None
    if raw.get("enabled", True) is False:
        return None
    rel_dir = str(raw.get("rel_dir") or "").strip().strip("/")
    loop = str(raw.get("loop") or "").strip()
    if not rel_dir or not loop:
        return None
    loop_name = Path(loop).name
    if not loop_name or loop_name != loop:
        return None
    return AutoagentsInfo(rel_dir=rel_dir, loop=loop_name)


def _parse_redmine_doc_issue_id(raw: object) -> int | None:
    if raw is None or raw is False:
        return None
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int):
        return raw if raw > 0 else None
    s = str(raw).strip()
    if not s or not s.isdigit():
        return None
    n = int(s)
    return n if n > 0 else None


def load_host_catalog(catalog_dir: Path, host: str) -> HostCatalog:
    path = catalog_dir / "hosts" / f"{host}.json"
    if not path.is_file():
        raise FileNotFoundError(f"Catalog missing for host {host!r}: {path}")
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Catalog root must be an object: {path}")
    host_name = str(raw.get("host") or host).strip().casefold() or host
    ssh_alias = str(raw.get("ssh_alias") or host_name).strip() or host_name
    projects: list[ProjectEntry] = []
    for item in raw.get("projects") or []:
        if not isinstance(item, dict):
            continue
        pid = str(item.get("id") or "").strip()
        path_s = str(item.get("path") or "").strip()
        if not pid or not path_s:
            continue
        aliases_raw = item.get("aliases") or []
        aliases = tuple(str(a).strip() for a in aliases_raw if str(a).strip())
        projects.append(
            ProjectEntry(
                id=pid,
                host=host_name,
                kind=str(item.get("kind") or "unknown").strip() or "unknown",
                path=Path(path_s).expanduser(),
                summary=str(item.get("summary") or "").strip() or "(no summary)",
                context_rel=str(item.get("context") or f"contexts/{pid}").strip(),
                aliases=aliases,
                active=bool(item.get("active", True)),
                ssh_alias=ssh_alias,
                autoagents=_parse_autoagents(item.get("autoagents")),
                redmine_doc_issue_id=_parse_redmine_doc_issue_id(
                    item.get("redmine_doc_issue_id")
                ),
            )
        )
    return HostCatalog(
        host=host_name,
        description=str(raw.get("description") or "").strip(),
        ssh_alias=ssh_alias,
        projects=tuple(projects),
    )


def load_catalog_index(catalog_dir: Path, local_host: str) -> CatalogIndex:
    hosts_dir = catalog_dir / "hosts"
    hosts: dict[str, HostCatalog] = {}
    if hosts_dir.is_dir():
        for path in sorted(hosts_dir.glob("*.json")):
            raw_host = path.stem.strip().casefold()
            cat = load_host_catalog(catalog_dir, raw_host)
            hosts[cat.host] = cat
    if not hosts:
        raise FileNotFoundError(f"No host catalogs under {hosts_dir}")
    return CatalogIndex(local_host=local_host.strip().casefold() or "lu-zero", hosts=hosts)


def context_pack_dir(repo_root: Path, entry: ProjectEntry) -> Path:
    rel = entry.context_rel
    p = Path(rel)
    if p.is_absolute():
        return p
    return (repo_root / rel).resolve()


def read_context_markdown(repo_root: Path, entry: ProjectEntry) -> str:
    ctx = context_pack_dir(repo_root, entry) / "CONTEXT.md"
    if ctx.is_file():
        return ctx.read_text(encoding="utf-8").strip()
    return f"(No CONTEXT.md for {entry.id} at {ctx})"


def format_list_projects(index: CatalogIndex, *, host_filter: str | None = None) -> str:
    """Format catalog listing. ``None`` / empty / ``all`` → every host, sectioned."""
    raw = (host_filter or "all").strip().casefold() or "all"
    if raw in {"all", "*"}:
        lines = ["**Maestro projects · all hosts**", ""]
        for host_name in index.list_hosts():
            lines.append(format_list_projects(index, host_filter=host_name))
            lines.append("")
        return "\n".join(lines).strip()

    cat = index.get_host(raw)
    if cat is None:
        available = ", ".join(f"`{h}`" for h in index.list_hosts()) or "(none)"
        return (
            f"Host `{raw}` is not in the Maestro catalog. "
            f"Available: {available}, or `all`."
        )

    lines = [f"**Maestro projects · `{cat.host}`**", ""]
    if cat.description:
        lines.append(cat.description)
        lines.append("")
    if cat.host != index.local_host:
        lines.append(
            f"Remote host — reach with `ssh {cat.ssh_alias}` "
            f"(cursor-agent runs on **{index.local_host}**)."
        )
        lines.append("")
    active = cat.active_projects()
    if not active:
        lines.append("_No active projects._")
        return "\n".join(lines)
    by_kind: dict[str, list[ProjectEntry]] = {}
    for p in active:
        by_kind.setdefault(p.kind, []).append(p)
    for kind in sorted(by_kind):
        lines.append(f"**{kind}**")
        for p in by_kind[kind]:
            aa = " · **autoagents**" if p.autoagents is not None else ""
            rm = (
                f" · RM#{p.redmine_doc_issue_id}"
                if p.redmine_doc_issue_id is not None
                else ""
            )
            lines.append(f"• `{p.id}`{aa}{rm} — {p.summary}")
            lines.append(f"  `{p.path}`")
            if p.autoagents is not None:
                lines.append(f"  loop `{p.autoagents.loop_path(p.path)}`")
        lines.append("")
    return "\n".join(lines).strip()
