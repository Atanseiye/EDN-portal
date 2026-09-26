#!/usr/bin/env sh
curl -sS http://localhost:8000/v1/chat/completions \
  -H 'content-type: application/json' \
  -d '{
    "model":"NCAIR1/N-ATLaS",
    "messages":[{"role":"user","content":"What is an API?"}],
    "temperature":0.2,
    "max_tokens":200
  }'
