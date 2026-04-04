#!/usr/bin/env bash
# Manage a labelled GitHub issue: open/comment-on, or close with a message.
#
# Usage:
#   manage_issue.sh file  LABEL TITLE BODY_FILE   — create issue or comment on open one
#   manage_issue.sh close LABEL MESSAGE            — comment + close if any open issue exists
#
# Requires GH_TOKEN in the environment (standard in GitHub Actions).

set -euo pipefail

ACTION="$1"
LABEL="$2"

if [ "$ACTION" = "file" ]; then
    TITLE="$3"
    BODY_FILE="$4"
    OPEN_COUNT=$(gh issue list --label "$LABEL" --state open --json number --jq length)
    if [ "$OPEN_COUNT" -eq 0 ]; then
        gh issue create --title "$TITLE" --label "$LABEL" --body-file "$BODY_FILE"
    else
        ISSUE_NUM=$(gh issue list --label "$LABEL" --state open --json number --jq '.[0].number')
        gh issue comment "$ISSUE_NUM" --body-file "$BODY_FILE"
    fi

elif [ "$ACTION" = "close" ]; then
    MESSAGE="$3"
    OPEN_COUNT=$(gh issue list --label "$LABEL" --state open --json number --jq length)
    if [ "$OPEN_COUNT" -gt 0 ]; then
        ISSUE_NUM=$(gh issue list --label "$LABEL" --state open --json number --jq '.[0].number')
        gh issue comment "$ISSUE_NUM" --body "$MESSAGE"
        gh issue close "$ISSUE_NUM"
    fi

else
    echo "Usage: manage_issue.sh (file LABEL TITLE BODY_FILE | close LABEL MESSAGE)" >&2
    exit 1
fi
