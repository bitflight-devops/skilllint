# Python typing policy

Version: 1.0
Applies to: Python 3.11+ (3.11 is the repository baseline)
Required libraries: [Pydantic](https://docs.pydantic.dev/), [Hypothesis](https://hypothesis.readthedocs.io/)

## 1. Purpose

This policy defines how we enforce strong typing in Python code. The goal is to keep unknown, weakly typed, or dynamically shaped data at the edges of the system and ensure that the internal codebase operates on validated, concrete types.

## 2. Core Rule

Inside the codebase, types must be explicit and enforced.

`Any`, `object`, and `cast()` are not general-purpose escape hatches. They are allowed only at typed boundaries where data enters the system without a trustworthy static shape, such as JSON, environment variables, tool output, LLM output, third-party API responses, file parsing, queues, and similar ingestion points. After crossing the boundary, the data must be validated and converted into a strongly typed internal model. **Pydantic is the required mechanism for this validation layer.** Pydantic is built around Python type hints, supports strict mode, supports validators and serializers, and includes `TypeAdapter` for validating annotated types directly.

## 3. Default Expectations

All internal modules must use precise annotations for function parameters, return values, variables, attributes, and containers.

The following are **forbidden** in normal application code:

- `Any`
- `object` used as a catch-all substitute for a real type
- `cast()` used to silence the type checker
- untyped `dict` or `list` values flowing through domain logic
- returning raw external payloads from internal service functions

The following are **required**:

- concrete domain models
- explicit unions where multiple shapes are valid
- `TypedDict`, dataclasses, or Pydantic models when structure matters
- validation at ingress, not downstream
- property-based tests for validators and adapters using Hypothesis

## 4. Typed Boundary Rule

A typed boundary is any function or module that accepts raw, external, or otherwise untrusted input.

Boundary code may temporarily use `Any`, `object`, or `cast()` only if **all** of the following are true:

1. The value originates outside the typed core.
2. The boundary function immediately validates the input.
3. The boundary function returns a concrete typed object.
4. No raw untyped value escapes the boundary.
5. Any use of `cast()` is justified by a prior runtime check, schema validation, or library guarantee.

`cast()` is not validation. It may only be used after a proof step.

## 5. Golden Path

Every new ingestion path must follow this sequence:

1. Accept raw input.
2. Validate and normalize raw input at the boundary.
3. Convert it into a **Pydantic model** or another explicitly typed internal object.
4. Return only the typed object.
5. Use only typed values in all downstream code.

In practice, this means:

- external `dict[str, Any]` in
- validated Pydantic model out
- typed domain code after that point

## 6. Required File and Naming Conventions

Boundary code must be isolated in dedicated files. Approved module names include:

- `*_validators.py`
- `*_adapters.py`
- `*_boundary.py`
- `*_ingest.py`
- `*_parsers.py`

In **this repository**, boundary modules also live under `packages/skilllint/boundary/` (same rules apply).

Approved function prefixes include:

- `parse_`
- `validate_`
- `decode_`
- `coerce_`
- `*_from_raw`

Examples:

- `parse_user_payload() -> UserPayload`
- `validate_order_event() -> OrderEvent`
- `decode_agent_response() -> AgentResponse`
- `tool_result_from_raw() -> ToolResult`

**Rule:** if a function accepts unknown shape, its name must make that fact obvious.

## 7. Linting and Repository Enforcement

Only approved boundary modules may contain narrow lint exclusions for `Any`.

Everywhere else:

- `Any` should fail linting
- unchecked `cast()` should fail review
- untyped boundary leakage should fail review
- domain modules should not import raw external payload types

**Recommended enforcement pattern:**

- boundary modules: narrowly scoped exceptions
- all other modules: strict no-`Any` policy

### skilllint repository

Astral **`ty`** is the single enforced type checker. The dedicated CI type job runs `uv run ty check packages/`. The prek hook runs `ty check` on the Python filenames passed to it, so it also covers repository tooling and tests. The package-only command is useful for targeted feedback but does not replace `uv run prek run --all-files` and `uv run pytest`, the repository completion gates. **`[tool.mypy]`** is effectively excluded and **`[tool.basedpyright]`** has `typeCheckingMode = "off"` to avoid overlapping type checks.

## 8. Pydantic Addendum

Pydantic is a required dependency. Apply these practices at ingestion boundaries:

### 8.1 Use Pydantic models as the default ingress contract

External payloads must be converted into `BaseModel` instances or validated typed structures immediately.

### 8.2 Prefer strict validation at boundaries

Use Pydantic strict mode for boundary validation where silent coercion would hide producer errors.

### 8.3 Use `TypeAdapter` for typed values that do not need a full model

For `list[Foo]`, `dict[str, Bar]`, unions, and other annotated types, prefer `TypeAdapter` over hand-written validation logic.

### 8.4 Centralize custom validation in validators, not ad hoc checks

If special coercion or normalization is required, do it in Pydantic validators or serializers so validation behavior stays declarative and testable.

### 8.5 Do not pass raw dicts past the model layer

Once a payload has been validated, pass the model or a typed domain object, not the original raw dictionary.

## 9. Hypothesis Addendum

Hypothesis is included in the development dependencies. Use it to exercise boundary behavior:

### 9.1 Property-test every boundary validator

Use Hypothesis to test that validators either accept valid shapes or fail cleanly on invalid ones.

### 9.2 Generate data from types whenever possible

Hypothesis provides `from_type()` to infer a strategy from a Python type. Use this to keep tests aligned with declared types instead of manually duplicating shape assumptions in test code.

### 9.3 Type your strategies and composite generators

Type composite strategies with `SearchStrategy[T]` so test helpers participate in the same typing discipline as production code.

### 9.4 Use Ghostwriter to bootstrap boundary tests

Hypothesis Ghostwriter can generate starter tests. It should be used as a starting point for human-authored tests, especially when adding new boundary adapters.

## 10. Python compatibility

Python 3.11 is the minimum supported version in `pyproject.toml`, and Ruff targets `py311`. Package syntax and imports must work on that baseline, even when the development interpreter is newer.

### 10.1 Available on the baseline

- Use `Self` for fluent APIs, alternate constructors, and methods that return the current class.
- Use `typing.assert_type()` in tests or type-check-only assertions to check inferred types at important boundaries.
- Use `typing.reveal_type()` during development to inspect inferred types.
- Use `TypeAlias` and the Python 3.11-compatible generic syntax for shared types. `packages/skilllint/models.py` contains examples.

### 10.2 Features introduced after Python 3.11

Python 3.12's `type` statement and generic parameter syntax cannot be parsed by Python 3.11. They are not suitable for package code while the current baseline remains supported.

Likewise, `typing.TypeIs`, `typing.ReadOnly`, and `annotationlib` are not available in the Python 3.11 standard library. If a change needs newer typing or annotation behavior, use a baseline-compatible approach and verify it on the supported Python versions. A newer development interpreter alone is not a reason to change the package's compatibility contract.

## 11. Allowed and Disallowed Examples

### Allowed

- `Any` inside `llm_boundary.py` while receiving unknown tool output, followed immediately by Pydantic validation into `AgentResponse`
- `object` in a parser that accepts a truly unknown external value and narrows it through checks
- `cast()` after a runtime discriminator check or validated schema step
- `TypeAdapter(list[OrderEvent]).validate_python(raw)` at ingress

### Disallowed

- `cast(User, payload)` without validation
- `dict[str, Any]` passed through service layers
- `Any` in domain models, business logic, repositories, or utilities
- returning raw JSON from adapter functions
- using `object` to avoid defining a union or protocol

## 12. Review Checklist

Before merging code, reviewers should ask:

1. Is unknown data isolated to an explicit boundary?
2. Does the boundary validate immediately?
3. Does it return a concrete typed object?
4. Does any raw untyped value leak into internal code?
5. Is every `cast()` justified by a prior proof step?
6. Could Pydantic `BaseModel` or `TypeAdapter` replace custom parsing?
7. Does Hypothesis cover malformed, partial, and edge-case inputs?
8. Do the syntax and imports work on the supported Python 3.11 baseline?

## 13. Non-Negotiable Standard

Unknown data may enter the system only through explicit boundary adapters. Boundary adapters may use limited untyped constructs only to ingest and validate raw input. After validation, the typed core must remain fully typed. `Any`, `object`, and unchecked `cast()` are exceptions for ingress only, never a substitute for modeling.
