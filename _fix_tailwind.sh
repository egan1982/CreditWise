#!/bin/bash
# Quick fix: revert Tailwind CDN removal
HTML_FILE=/app/llm_manager_integrated/static/index.html
ASSETS_FILE=/app/llm_manager_integrated/static/assets/index.html

for f in $HTML_FILE $ASSETS_FILE; do
  docker exec creditwise-api sed -i 's|<link rel=.stylesheet. href=./llm-manager/static/tailwind.css.>|<script src="https://cdn.tailwindcss.com?plugins=forms,typography,aspect-ratio,line-clamp"></script>|' "$f"
done
echo "CDN restored"
