SAMFpy Client

This repository contains a TUI client and helper scripts.

# Docker multi-arch publishing

To publish a multi-arch image (linux/amd64 & linux/arm64) to Docker Hub via GitHub Actions:

1. Create Docker Hub repo: docker.io/<your-username>/samfpy-client
2. Add GitHub repository secrets:
   - DOCKERHUB_USERNAME
   - DOCKERHUB_TOKEN
3. Push to branch `main`, `master`, or `keypairs` to trigger the workflow. You can also run it manually via "Actions" -> "Build and publish multi-arch image" -> "Run workflow".

Or build locally with buildx:

```bash
docker buildx create --use --bootstrap
docker buildx build --platform linux/amd64,linux/arm64 -t USERNAME/samfpy-client:latest --push .
```

If pip fails for arm64 due to missing wheels, ensure the Dockerfile includes the necessary system build dependencies (this repo already adds a conservative set: gcc, g++, libffi-dev, libsodium-dev, cargo, python3-dev).

