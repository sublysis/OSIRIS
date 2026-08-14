# Interpreting Scores

This tool produces two different kinds of numbers that look similar but mean
very different things: **stylometric similarity** (a real similarity metric)
and **link scores** (a heuristic evidence tally). Confusing the two leads to
over-reading the results. This document explains both, plus how to read a
report responsibly.

## 1. Stylometric similarity (`--nlp`)

Computed in `osint/nlp/stylometry.py`: character n-gram (2-4) TF-IDF vectors
per document, compared with **cosine similarity**.

```
0.173  https://traack.com/  <->  https://privatesystems.net
0.67   Stil-Aehnlichkeit (used as evidence inside a link)
```

- Range: `0.0` (no overlap in character-level style) to `1.0` (identical).
- It is a genuine similarity metric — but it measures **surface writing
  style** (function words, punctuation density, sentence/word length,
  character n-grams), not authorship in a legally or statistically rigorous
  sense.
- **Not a p-value, not a probability of "same author."** Two unrelated
  pages can score moderately high just because they're both short, both
  written in formal English, or both contain a lot of boilerplate
  (navigation text, copyright notices, contact blocks).
- Short texts (see `privatesystems.net`, 293 characters in the earlier
  example) are noisy — few characters means the n-gram vector is mostly
  boilerplate, and similarity scores for very short documents should be
  trusted less than for longer ones.
- `config.nlp.stylometry_threshold` (default `0.0`) only controls what's
  *printed* in the CLI summary — it does not filter what feeds into
  correlation.

**How to read it:** treat it as "these two texts share more/less
character-level style than average," a lead to investigate further
(e.g. read both texts yourself), not a conclusion.

## 2. Link scores (`--correlate`)

This is the number that shows up in reports as e.g. `**0.80**` next to a
pair of selectors. **It is not a correlation coefficient, not a standard
deviation, and not a statistical measure of any kind.**

From `osint/correlate/linker.py`:

```python
score = min(1.0, sum(e.weight for e in evs))
```

It's a **capped sum of weighted evidence items**. Each piece of evidence
that links two selectors (two emails, two names, a name and an email, a URL
and a URL, ...) contributes a fixed weight, defined in
`config/default.yaml`:

| Evidence kind | Meaning | Default weight |
|---|---|---|
| `shared_domain` | both selectors turned up results/accounts pointing at the same domain (e.g. both found via a `twitter.com` account, or via the same search-result domain) | 0.4 |
| `shared_entity` | both selectors co-occur with the same named entity (person/org/email/handle) extracted by NER | 0.6 |
| `seed_in_doc` | one selector's literal value appears inside a document fetched for another artifact | 0.7 |
| `stylometry` | `0.5 × cosine similarity` of the two documents' style vectors | up to 0.5 |

A score of `0.80` most commonly means **two independent pieces of evidence
of weight 0.4 each** (e.g. two shared domains) — it does *not* mean "80%
confidence these are the same person." A single strong `seed_in_doc` hit
(0.7) plus a `shared_domain` hit (0.4) would be capped at `1.0`, the same
ceiling as five weak hits combined.

`config.correlate.min_score` (default `0.3`) is just the cutoff for a link
to appear in the report at all — it is not a confidence threshold.

**How to read it:**
- Higher score = more independent, differently-typed pieces of evidence
  agree, which is *more* interesting than fewer/weaker pieces.
- Always open the `evidence` list (or the bullet points under each link in
  the report) and check *what kind* of evidence is behind the number. Two
  `shared_domain` hits from the same generic platform (e.g. both found on
  `facebook.com` because they searched a common term) is much weaker
  evidence than one `seed_in_doc` hit (a name or email literally printed on
  someone's page).
- The score is capped at `1.0`, so `0.80` and a hypothetical `1.20` (before
  capping) look identical in the report — the raw evidence list is where the
  real weight of the finding lives, not the headline number.
- Because weights are configurable (`config.correlate.weights`), the same
  evidence can produce different scores across installations/configs. Don't
  compare scores across differently-configured runs without checking the
  weights first.

### A common misreading, corrected

It's tempting to phrase a `0.80` link as *"X and Y are 80% likely to share
authorship"* or *"the evidence that X and Y are linked is 80/100, therefore
probably causal."* Both are wrong, for two separate reasons:

1. **There is no calibrated 0-100 scale.** The weights (0.4, 0.6, 0.7, 0.5 ×
   similarity) are arbitrary values set in `config/default.yaml`, not
   probabilities derived from data. `0.80` does not mean "80 out of 100
   possible points in a calibrated system" — it means "the weights of the
   evidence types that were found happened to sum to 0.80," capped at
   `1.0`. There's no basis for treating `0.80` as measurably "more likely"
   than `0.75` in any statistical sense — only as backed by more/stronger
   evidence.

2. **The score measures co-occurrence, not causation, and usually isn't
   about authorship at all.** "Authorship"/writing style is only one of
   four evidence kinds (`stylometry`). The other three
   (`shared_domain`, `shared_entity`, `seed_in_doc`) say nothing about
   writing style — they indicate **shared identity/association** (e.g. the
   same person operating multiple accounts, or two selectors appearing in
   the same context), which is a different claim than "same author." A link
   score has nothing to do with causality; it's a co-occurrence tally.

A more accurate phrasing for a `0.80` link backed by two `shared_domain`
hits:

> "Two independent, equally-weighted pieces of evidence (both of type
> 'shared source') connect X and Y, summing to a score of 0.80 (capped at
> 1.0). This is a lead worth verifying manually — it is not a probability,
> not a causal claim, and — unless `stylometry` evidence is present — not a
> statement about shared authorship at all."

Only check for shared authorship/writing style when `stylometry` evidence
specifically appears in the link's evidence list — and even then, it's a
cosine similarity of style vectors, not proof of authorship (see the
short-document caveat above).

## 3. Practical checklist before drawing conclusions

1. Look at the **evidence list**, not just the score.
2. For `stylometry` evidence, check document length — very short pages
   inflate noise.
3. For `shared_domain`, check *which* domain — a generic platform (Facebook,
   Twitter/X, a search engine result domain) is weaker evidence than a
   niche/private domain.
4. Treat everything as a **lead**, not a verdict. This tool surfaces
   correlations for a human to verify manually (read the actual pages,
   check the actual accounts) — it does not itself confirm identity.
5. Remember GDPR/legal constraints (see the "Rechtlich" section in the main
   README) before acting on or storing conclusions about real people.
