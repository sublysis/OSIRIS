from dataclasses import dataclass, field


@dataclass
class Evidence:
    kind: str      # stylometry | shared_domain | shared_entity | seed_in_doc
    detail: str
    weight: float


@dataclass
class Target:
    key: str       # kanonischer Dedup-Schluessel
    kind: str      # url | account
    value: str
    sources: list = field(default_factory=list)  # [{"seed":.., "via":.., "url":..}]

    @property
    def seed_count(self):
        return len({s["seed"] for s in self.sources})


@dataclass
class Link:
    a: str
    b: str
    score: float
    evidence: list = field(default_factory=list)  # list[Evidence]


@dataclass
class CorrelationResult:
    targets: list  # list[Target]
    links: list    # list[Link]

    def to_dict(self):
        return {
            "targets": [
                {
                    "key": t.key,
                    "kind": t.kind,
                    "value": t.value,
                    "seed_count": t.seed_count,
                    "sources": t.sources,
                }
                for t in self.targets
            ],
            "links": [
                {
                    "a": l.a,
                    "b": l.b,
                    "score": l.score,
                    "evidence": [{"kind": e.kind, "detail": e.detail, "weight": e.weight} for e in l.evidence],
                }
                for l in self.links
            ],
        }
