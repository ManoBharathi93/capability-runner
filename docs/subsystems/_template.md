# Subsystem: <accepted component name>

## Status

- Design: **ACCEPTED BASELINE** or **PROPOSED IMPLEMENTATION DETAIL**
- Implementation: `not started`, `in progress`, `implemented`, or `blocked`
- Verification: `not run`, `passed`, `failed`, or `inconclusive`
- Authorized milestone: `<milestone>`

## Before implementation

### 1. Problem

What concrete problem does this block solve in the required execution path?

### 2. Input and output contract

Name the concrete typed inputs, outputs, errors, and async behavior. Keep examples illustrative until tests exist.

### 3. State and dependencies

State owned by this block, dependencies it may use, and dependencies it must not use.

### 4. Accepted direction

Relevant accepted decision and how this subsystem applies it without reopening the architecture.

### 5. Alternatives considered

One or two credible alternatives and why they were not selected for this scope.

### 6. Costs and failure modes

Limitations, operational costs, unsafe edge cases, and ways the chosen boundary could fail.

### 7. Boundary and assumption tests

Tests that would expose an incorrect contract, forbidden dependency, or failed architectural assumption.

## After implementation

### 8. Actual files and behavior

List implemented files and observable behavior. Do not list planned files as implemented.

### 9. Commands and results

Record date, environment/version, exact command or manual procedure, expected result, observed result, pass/fail/inconclusive status, and sanitized evidence path.

### 10. Known limits and next integration

State remaining limits, unresolved details, and the smallest authorized integration point. Stop before the next subsystem unless it is separately authorized.