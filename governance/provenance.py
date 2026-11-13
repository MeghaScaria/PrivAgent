"""
Per-run provenance registry. Every item a governed MCP tool call returns
gets a data reference (ref) here, at the governance boundary in
agents/tools.py. When an agent turns inputs into something new (a plan,
an analysis, a final answer), a derived ref records which refs it was
built from, so any piece of data can be traced back to the tool calls
that produced it.

Items are matched to refs by a fingerprint of their content, not by
tagging the data itself, so the agents (and the LLM prompts) see exactly
the same data as without instrumentation. Fingerprints are keyed with a
random per-registry secret (HMAC), live in memory only, and are never
written to logs: a plain hash of a low-entropy record (a salary, an
account number) could be confirmed by guessing.

Sensitivity is stored as {"value": 0 | 1 | None, "basis": why}, so it's
always clear whether a label came from the data source, was inherited
from inputs, or is unknown (None). See governance/sensitivity.py.

The registry also tracks what each agent role has received (tool results
it fetched, handoffs it consumed). Anything an agent sends onward can
only be built from those inputs, so agent_label() is the authoritative
sensitivity of an agent's outbound data.
"""
import hashlib
import hmac
import json
import secrets

from governance.sensitivity import combine

SENSITIVE_TABLES = {"employees", "transactions"}
TOOL_TO_SERVER = {
    "search_documents": "document_server", "retrieve_document": "document_server",
    "query_database": "database_server", "list_tables": "database_server",
    "search_web": "web_server",
    "send_result": "external_server", "get_transmission_log": "external_server",
}


# Fields kept in memory but left out of anything written to a log.
PRIVATE_REF_FIELDS = {"fingerprint"}


def fingerprint(item, key):
    canonical = json.dumps(item, sort_keys=True, default=str)
    return hmac.new(key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()


def item_sensitivity(tool_name, args, item):
    """Item-level label for one returned item, using the most specific
    information the source gives."""
    if tool_name in ("search_documents", "retrieve_document") and isinstance(item, dict):
        if "sensitivity" in item:
            return {"value": int(item["sensitivity"] == "high"), "basis": "document_label"}
        doc_id = str(item.get("id", ""))
        return {"value": int(doc_id.startswith(("hr_", "finance_"))), "basis": "document_id_prefix"}
    if tool_name == "query_database":
        return {"value": int(args.get("table") in SENSITIVE_TABLES), "basis": "table_policy"}
    if tool_name == "search_web":
        return {"value": 0, "basis": "public_web"}
    if tool_name in ("send_result", "get_transmission_log"):
        # Both echo a preview of outbound payloads, which can be anything.
        return {"value": None, "basis": "echoes_outbound_payload"}
    return {"value": 0, "basis": "metadata_only"}


def _item_locator(tool_name, args, item):
    if isinstance(item, dict):
        if tool_name in ("search_documents", "retrieve_document") and "id" in item:
            return f"doc:{item['id']}"
        if tool_name == "query_database" and "id" in item:
            return f"{args.get('table')}#{item['id']}"
        if tool_name == "search_web" and "url" in item:
            return item["url"]
    return "item"


class ProvenanceRegistry:
    def __init__(self):
        self.refs = {}
        self._by_fingerprint = {}
        self._counter = 0
        self._key = secrets.token_bytes(32)
        self.agent_inputs = {}

    def _fp(self, item):
        return fingerprint(item, self._key)

    def snapshot(self, ref_id):
        """A ref as it may be written to a log: metadata and references only."""
        return {k: v for k, v in self.refs[ref_id].items() if k not in PRIVATE_REF_FIELDS}

    def note_received(self, agent_role, ref_ids):
        received = self.agent_inputs.setdefault(agent_role, [])
        received.extend(r for r in ref_ids if r not in received)

    def agent_label(self, agent_role):
        """Authoritative sensitivity of anything this agent produces: the
        combination of everything it has received. Unknown if nothing
        was recorded for it."""
        received = self.agent_inputs.get(agent_role, [])
        if not received:
            return {"value": None, "basis": "no_recorded_inputs", "refs": []}
        value = combine(self.refs[r]["sensitivity"]["value"] for r in received)
        return {"value": value, "basis": "agent_inputs", "refs": list(received),
                "sensitive_refs": [r for r in received
                                   if self.refs[r]["sensitivity"]["value"] == 1],
                "unknown_refs": [r for r in received
                                 if self.refs[r]["sensitivity"]["value"] is None]}

    def _new_ref(self, **fields):
        self._counter += 1
        ref_id = f"ref{self._counter}"
        self.refs[ref_id] = {"ref_id": ref_id, **fields}
        return ref_id

    def register_tool_result(self, tool_name, args, result, decision_event_id, agent_role):
        """Registers every item of an allowed tool call's result. Returns
        the new ref ids, in result order."""
        items = result if isinstance(result, list) else ([result] if result is not None else [])
        ref_ids = []
        for item in items:
            fp = self._fp(item)
            if fp in self._by_fingerprint:
                ref_ids.append(self._by_fingerprint[fp])
                continue
            ref_id = self._new_ref(
                kind="tool_result",
                source=f"{TOOL_TO_SERVER.get(tool_name, 'unknown')}:{tool_name}:"
                       f"{_item_locator(tool_name, args, item)}",
                sensitivity=item_sensitivity(tool_name, args, item),
                produced_by=agent_role,
                via_tool=tool_name,
                tool_event_id=decision_event_id,
                derived_from=[],
                fingerprint=fp,
            )
            self._by_fingerprint[fp] = ref_id
            ref_ids.append(ref_id)
        self.note_received(agent_role, ref_ids)
        return ref_ids

    def lookup(self, item):
        """The ref for an item seen in agent state. An item no governed
        tool call returned gets an 'unregistered' ref with unknown
        sensitivity, so it shows up in the handoff instead of vanishing."""
        fp = self._fp(item)
        if fp in self._by_fingerprint:
            return self._by_fingerprint[fp]
        ref_id = self._new_ref(
            kind="unregistered", source=None,
            sensitivity={"value": None, "basis": "not_from_governed_tool_call"},
            produced_by=None, via_tool=None, tool_event_id=None,
            derived_from=[], fingerprint=fp,
        )
        self._by_fingerprint[fp] = ref_id
        return ref_id

    def register_root(self, kind, produced_by, sensitivity, content=None):
        """A ref with no parents, e.g. the user's task text."""
        return self._new_ref(
            kind=kind, source=produced_by, sensitivity=sensitivity,
            produced_by=produced_by, via_tool=None, tool_event_id=None,
            derived_from=[], fingerprint=self._fp(content) if content is not None else None,
        )

    def derive(self, kind, produced_by, parents, content=None):
        """Something an agent produced from its inputs. Its sensitivity is
        the highest of its parents' (1 if any input was sensitive); it's
        unknown if a parent is unknown and none is sensitive."""
        value = combine(self.refs[p]["sensitivity"]["value"] for p in parents)
        return self._new_ref(
            kind=kind, source=produced_by,
            sensitivity={"value": value, "basis": "inherited_max" if parents else "no_inputs"},
            produced_by=produced_by, via_tool=None, tool_event_id=None,
            derived_from=list(parents),
            fingerprint=self._fp(content) if content is not None else None,
        )

    def origins(self, ref_id):
        """The root refs (tool results, task input) a ref traces back to."""
        seen, stack, roots = set(), [ref_id], []
        while stack:
            r = stack.pop()
            if r in seen:
                continue
            seen.add(r)
            parents = self.refs[r]["derived_from"]
            if parents:
                stack.extend(parents)
            else:
                roots.append(r)
        return sorted(roots, key=lambda r: int(r[3:]))
