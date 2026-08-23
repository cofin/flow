---
type: Guide
title: Core Domain Context & Glossary
description: Domain entities, ubiquitous language, and explicit synonym avoidance rules.
scope: domain
domain: core
tags: [domain, glossary, ubiquitous-language]
status: stable
---

# Core Domain Context

## Ubiquitous Language

- **Entity**: The canonical domain object representing a persistent business identity.
  - _Avoid_: record, row, object, item
- **Session**: The active authenticated lifecycle between a client and the application.
  - _Avoid_: connection, login, token-holder
- **Dispatch**: Sending exactly one task worksheet to an executor subagent.
  - _Avoid_: batch-send, fan-out, queue-job
