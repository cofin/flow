---
type: Guide
title: Architecture Overview
description: High-level architectural structure, system boundaries, and core data flow.
scope: architecture
tags: [architecture, overview, system-design]
status: stable
---

# Architecture Overview

## System Boundaries

- **Core Module**: Encapsulates business logic and domain entities.
- **Data Access Layer**: Repositories and adapters isolating persistence from domain models.
- **Presentation & API Layer**: Handlers, controllers, and DTO validation.

## Data Flow

1. Request enters the controller and is validated via typed DTOs.
2. Controller delegates execution to domain services.
3. Services interact with repositories to query and persist state.
4. Response is serialized back to the caller through explicit output schemas.
