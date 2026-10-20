
1. Create an input file with the artifacts you want to investigate:

```bash
cat > targets.txt <<'EOF'
url:https://example.com
url:https://example.com/about
email:info@example.com
username:examplecorp
name:Jane Doe
EOF
```

2. Run the full pipeline: fetch page text + favicon, look up WHOIS and Certificate Transparency data, run NLP (NER/keyphrases/stylometry), search the selectors on the web + maigret/holehe, correlate shared sources/style/registrants/favicons/certs, persist the run, and write reports (including a graph export for Gephi/Maltego):

```bash
python cli.py targets.txt --fetch --whois --certs --nlp --search --correlate --save --report md,html,graphml --json out.json
```

3. Re-run later against the same file to see what changed:

```bash
python cli.py targets.txt --nlp --search --correlate --monitor --save
```

4. Inspect all stored runs for this input file:

```bash
python cli.py targets.txt --history
```

If you want automatic artifact discovery (e.g. crawling `example.com` for sitemap links, emails, or social handles), that's a separate feature, not part of `cli.py` today.

