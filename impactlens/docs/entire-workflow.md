# Entire Buildathon Workflow

This repository is designed for the Participant Guide's **Track 2 — Build with Graph Intelligence**. The official workflow requires implementation in the clone created through Entire's mirror workflow.

## Before implementation

Research and planning may happen before kickoff, but implementation begins after the official start.

## Required commands

Replace placeholders with your own GitHub handle/repository when executing these commands; do not commit the values.

```bash
entire login
entire repo mirror create
entire repo clone /gh/YOUR-GITHUB-HANDLE/REPOSITORY
cd REPOSITORY
entire enable -y --agent YOUR-BUILD-AGENT
entire status
entire plugin install graph
entire graph version
entire graph init-agents --repo .
```

Start a fresh coding-agent session after Graph activation. The guide requires checkpoints for:

1. Initial understanding and intended architecture.
2. Last stable state before noon.
3. Response to the official Noon Curveball.
4. Final implementation and verification.

## Graph evidence to record

Before a high-risk change, record an impact analysis. During development, show at least a graph search/definition lookup, an impact/relationship analysis, and a final semantic diff. Verify graph findings against source/tests.

The current Entire Graph documentation confirms the query family `search`, `def`, `neighbors`, `impact`, `diff`, and `snapshot`, and explicitly describes graph results as evidence to be checked against source.

## Curveball

At noon, stop, preserve the stable checkpoint, close the coding-agent session, receive only the official constraint, start a fresh session, reconstruct from checkpoint context, run graph impact before editing the affected area, implement the smallest complete response, test it, and create a new checkpoint.

The constraint is intentionally not included in this repository before the event reveals it.
