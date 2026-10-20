# How to start and run the local SearXNG Container

## Start the container 

(only reachable locally, not public)

```shell
sudo docker rm -f searxng >/dev/null 2>&1 || true
sudo docker run -d --name searxng --restart unless-stopped \
  -p "127.0.0.1:8080:8080" \
  -v "$SEARXNG_DIR:/etc/searxng" \
  searxng/searxng:latest
```

**Then briefly test whether the JSON API responds:**

```bash
curl -s "http://127.0.0.1:8080/search?q=test&format=json" | head -c 200
```


**Control container**

```bash
docker stop searxng    # stop
docker start searxng   # start again later
```

If the first request is still empty/erroneous: SearXNG needs a few seconds to start up on the very first launch (check with docker logs searxng). After that, --search in cli.py should run without "Connection refused".

Security note: -p "127.0.0.1:8080:8080" deliberately binds the container to localhost only, not publicly reachable — please don't change it to 0.0.0.0 unless you intentionally want to expose SearXNG.