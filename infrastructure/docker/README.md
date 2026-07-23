# infrastructure/docker

Reserved for shared or base Docker assets that aren't owned by a single service
(for example, a future reverse proxy or nginx image). Per-service Dockerfiles
live next to their code — `frontend/Dockerfile` and `backend/Dockerfile` — so
each service's build context stays simple and self-contained.
