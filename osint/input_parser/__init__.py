from .classifier import Artifact, ArtifactType, classify_line

__all__ = ["Artifact", "ArtifactType", "classify_line", "parse_file", "group_by_type"]


def parse_file(path, config=None):
    comment_prefix = "#"
    if config:
        comment_prefix = config.get("input", {}).get("comment_prefix", "#")

    artifacts = []
    with open(path, encoding="utf-8") as f:
        for raw in f:
            art = classify_line(raw, comment_prefix=comment_prefix)
            if art:
                artifacts.append(art)
    return artifacts


def group_by_type(artifacts):
    groups = {}
    for a in artifacts:
        groups.setdefault(a.type, []).append(a)
    return groups
