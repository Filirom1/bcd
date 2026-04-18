# Quality Gate Checklist - [Feature Name]

**Feature ID**: [feature-id]
**Implementation Date**: [YYYY-MM-DD]
**Implementer**: [Name/Claude]
**Architect Reviewer**: [Name]

---

## Pre-Implementation Gate ✓

Completed before running `/speckit.implement`:

- [ ] `/speckit.analyze` executed successfully
- [ ] Zero CRITICAL issues reported
- [ ] All constitution violations resolved
- [ ] Ambiguities clarified via `/speckit.clarify`
- [ ] Approval granted to proceed with implementation

**Pre-Implementation Sign-off**: ___________ Date: ___________

---

## Post-Implementation Gate

### 1. Automated Validation

Run `./scripts/quality-gate.sh` from repository root:

- [ ] ✅ All tests pass (unit, integration, e2e)
- [ ] ✅ Zero TODO/FIXME/HACK comments in production code
- [ ] ✅ Zero fake/mock/placeholder implementations
- [ ] ✅ Test coverage ≥80% for new code
- [ ] ✅ No custom implementations where libraries exist (Principle #2)

**Automated Check Results**:
```
[Paste output of ./scripts/quality-gate.sh here]
```

### 2. Constitution Re-Validation

Re-run `/speckit.analyze` after implementation:

- [ ] `/speckit.analyze` executed post-implementation
- [ ] Zero CRITICAL findings
- [ ] Zero MAJOR findings
- [ ] All MEDIUM findings documented below and accepted

**MEDIUM Findings** (if any):
```
[List MEDIUM findings from /speckit.analyze output]

Acceptance Rationale:
[Explain why each MEDIUM finding is acceptable or provide remediation plan]
```

### 3. Constitution Compliance Checklist

Verify compliance with all constitution principles:

- [ ] **I. Code Quality & DRY**: No duplicated logic, constants centralized
- [ ] **II. Library-First**: Used existing libraries (no NIH syndrome)
- [ ] **III. Comprehensive Testing**: 80%+ coverage, tests follow AAA pattern
- [ ] **IV. UX Consistency**: UI/CLI patterns match existing conventions
- [ ] **V. Click Minimization**: Primary actions ≤2 steps, smart defaults
- [ ] **VI. Performance**: Works on legacy hardware (tested or justified)
- [ ] **VII. Database Versioning**: Schema changes via Alembic migrations
- [ ] **VIII. Research-First**: Researched existing solutions before design
- [ ] **IX. Design-First**: Mockups/contracts approved before implementation
- [ ] **X. Internationalization**: en/fr translations complete, no hard-coded strings
- [ ] **XI. Quality Gates**: This checklist completed properly

### 4. Architecture Review (Claude AI Architect)

**Reviewer**: [Architect Name]
**Review Date**: [YYYY-MM-DD]

#### Code Review Findings

| ID | Severity | Location | Issue | Resolution |
|----|----------|----------|-------|------------|
| AR-1 | [CRITICAL/MAJOR/MEDIUM/LOW] | [file:line] | [Description] | [Fix/Accept] |
| AR-2 | | | | |
| AR-3 | | | | |

**Severity Summary**:
- CRITICAL: [ ] 0 findings (required for merge)
- MAJOR: [ ] 0 findings (required for merge)
- MEDIUM: [ ] 0 findings (or all documented and accepted above)
- LOW: ___ findings (acceptable, listed as suggestions)

#### Architecture Integration Review

- [ ] Follows service-layer pattern (business logic in `services/`)
- [ ] Pydantic schemas defined for API contracts
- [ ] Database changes use Alembic migrations (if applicable)
- [ ] i18n files updated (en/fr) with no hard-coded strings
- [ ] Error handling consistent with existing patterns
- [ ] Logging follows project conventions
- [ ] Security best practices applied (no SQL injection, XSS, etc.)

#### Cross-Platform Compatibility

- [ ] File paths use platform-agnostic handling (pathlib)
- [ ] Tests pass on Linux
- [ ] Tests pass on Windows (or N/A documented)

#### Performance Validation

- [ ] No N+1 query patterns
- [ ] Pagination implemented for collections
- [ ] Resource usage within bounds (memory, CPU)
- [ ] Performance tested on target hardware (or justified)

**Architect Notes**:
```
[Additional observations, suggestions, or concerns]
```

---

## Merge Decision

**Overall Status**: [ ] APPROVED FOR MERGE / [ ] BLOCKED (requires fixes)

**Blocking Issues** (if any):
```
[List any CRITICAL/MAJOR/MEDIUM findings that must be resolved before merge]
```

**Final Sign-off**:
- Implementer: ___________ Date: ___________
- Architect: ___________ Date: ___________

---

## References

- Constitution: `.specify/memory/constitution.md` (v1.2.0)
- Feature Spec: `specs/[feature-id]/spec.md`
- Implementation Plan: `specs/[feature-id]/plan.md`
- Task List: `specs/[feature-id]/tasks.md`
- Automated Gate Script: `scripts/quality-gate.sh`
