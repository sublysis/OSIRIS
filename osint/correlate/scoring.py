DEFAULT_WEIGHTS = {
    "stylometry": 0.5,
    "shared_domain": 0.4,
    "shared_entity": 0.6,
    "seed_in_doc": 0.7,
    "shared_registrant": 0.5,
    "shared_favicon": 0.6,
    "shared_cert": 0.7,
}


def resolve_weights(config):
    weights = dict(DEFAULT_WEIGHTS)
    override = (config.get("correlate", {}) or {}).get("weights") or {}
    weights.update(override)
    return weights
