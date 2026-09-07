---
name: explain-file
description: Deep, code-grounded explanation of a specific file or module - traces exact symbols (classes/methods/constants), failure modes, inputs/dependencies, outputs/side effects, and explicit architectural boundaries, using a strict fixed-section template. Use when asked to explain, trace, or document how a specific file/module works.
---

# Explaining a specific file or module

Use this when the user references a specific file, module, or symbol and
wants to understand how it actually works. This is not a general
architecture overview - for how this repo fits into the broader Artemis
pipeline, use `/explain-artemis-context` instead.

## 1. Identify the target file & context

Read the message carefully to extract the exact file path or module name
referenced. Locate its position and direct dependencies (what it imports,
what imports it) within the codebase without speculating beyond the
provided source - read the file itself and its direct imports/importers;
don't describe behavior you haven't actually read.

## 2. Enforce grounded code traceability

Anchor every operational claim directly to the code. Cite specific class
names, methods, constants, or key variables responsible for the logic
(e.g., `process_stream()`, `Config.BATCH_SIZE`) - never describe behavior
in the abstract when a concrete symbol is available to point at.

## 3. Analyze failure modes & error handling

Explicitly map how the file handles failures: document handled exceptions,
silent fallbacks, unhandled edge cases, and logging behavior. Highlight
potential points of failure or data loss.

## 4. Formulate the explanation using the strict output template

Format the entire response using exactly this structure, in this order,
with these exact section headers:

- **Purpose (Why):** A direct, single-sentence statement of why this file
  exists and the core problem/domain it solves.
- **Core Mechanism (How & What):** Step-by-step logic tracing execution
  flow, key transformations, and internal mechanics, grounded by cited
  symbols.
- **Inputs & Dependencies:** Required parameters, imported modules, data
  schemas, environment variables, or external configurations.
- **Outputs & Side Effects:** Return values, emitted events,
  database/file mutations, or state modifications.
- **Failure Modes:** Explicit error handling, raised exceptions,
  fallbacks, and crash points.
- **Explicit Exclusions:** Architectural boundaries - what this file
  purposefully delegates to other files or layers.

## 5. Acknowledge boundaries & gaps

If critical context is missing, imported code falls outside what's been
read, or any logic is ambiguous, state the limitation plainly instead of
guessing or speculating.
