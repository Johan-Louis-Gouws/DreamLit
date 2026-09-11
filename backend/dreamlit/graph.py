import hashlib


def build_graph(store, date_from=None, date_to=None, kind=None):
    dreams = [
        d
        for d in store.list_dreams()
        if (not date_from or str(d.dreamed_on) >= date_from)
        and (not date_to or str(d.dreamed_on) <= date_to)
    ]
    ids = {d.id for d in dreams}
    nodes = {
        d.id: dict(
            id=d.id,
            label=(d.text[:64] or "Voice note"),
            kind="dream",
            dream_id=d.id,
            pattern_id=None,
            date=str(d.dreamed_on),
        )
        for d in dreams
    }
    edges = []
    seen_patterns = set()
    entities = {}
    for analysis in store.list_analyses():
        if analysis["stale"]:
            continue
        for pattern in analysis["patterns"]:
            refs = {r["dream_id"] for r in pattern["evidence"]} & ids
            signature = (
                pattern["title"].casefold(),
                tuple(sorted(refs)),
                analysis["provider"],
            )
            if len(refs) < 2 or signature in seen_patterns or (kind and kind != "theme"):
                continue
            seen_patterns.add(signature)
            node_id = "pattern:" + pattern["id"]
            nodes[node_id] = dict(
                id=node_id,
                label=pattern["title"],
                kind="theme",
                dream_id=None,
                pattern_id=pattern["id"],
            )
            for source in refs:
                edges.append(
                    dict(
                        id=f"{node_id}:{source}",
                        source=source,
                        target=node_id,
                        kind="inferred",
                        analysis_id=analysis["id"],
                    )
                )
        for item in analysis["output"]["observations"]:
            if (
                item["kind"] not in ("character", "place")
                or item["inferred"]
                or (kind and item["kind"] != kind)
            ):
                continue
            # Shared labels indicate a textual recurrence, not an identity merge.
            key = (item["kind"], item["label"].casefold())
            entry = entities.setdefault(
                key, dict(label=item["label"], kind=item["kind"], sources={}, evidence={})
            )
            for ref in item["evidence"]:
                if ref["dream_id"] in ids:
                    entry["sources"][ref["dream_id"]] = analysis["id"]
                    entry["evidence"][ref["dream_id"]] = ref
    for key, item in entities.items():
        if len(item["sources"]) < 2:
            continue
        node_id = "entity:" + hashlib.sha256(str(key).encode()).hexdigest()[:16]
        nodes[node_id] = dict(
            id=node_id,
            label=item["label"],
            kind=item["kind"],
            dream_id=None,
            pattern_id=None,
            evidence=list(item["evidence"].values()),
        )
        for source, analysis_id in item["sources"].items():
            edges.append(
                dict(
                    id=f"{node_id}:{source}",
                    source=source,
                    target=node_id,
                    kind="observed",
                    analysis_id=analysis_id,
                )
            )
    return dict(
        nodes=list(nodes.values()),
        edges=edges,
        scope=dict(
            included_dream_ids=list(ids),
            total_eligible_dreams=len(store.list_dreams()),
            truncated=len(ids) < len(store.list_dreams()),
        ),
    )
