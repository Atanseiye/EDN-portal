#!/usr/bin/env sh
curl -sS https://ednai-6znf.onrender.com/v1/audio/transcriptions \
  -F 'language=yoruba' \
  -F 'file=@sample.wav'
