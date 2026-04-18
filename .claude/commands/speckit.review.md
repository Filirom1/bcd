---
description: Post-implementation quality gate review - validates completed implementation against spec, plan, constitution, and automated quality checks before merge approval
---

## User Input

```text
$ARGUMENTS
```

You **MUST** consider the user input before proceeding (if not empty).

## Goal

Perform comprehensive post-implementation validation as the final quality gate before merge approval. This command implements Constitution Principle #11 (Quality Gate Process) - Post-Implementation Gate validation.

**Deployment Context**: This software runs on localhost/LAN for elementary school librarians. Focus is on data integrity, usability, and performance - not security against attacks.

## Operating Constraints

**Read-Only Analysis**: This command does NOT modify code. It produces a review report with findings classified by severity (CRITICAL/MAJOR/MEDIUM/LOW) and provides merge recommendation.

**Constitution Authority**: Principle #11 violations are automatically CRITICAL and MUST block merge.

## Execution Steps

### 1. Initialize Review Context

Run `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` once from repo root and parse JSON for:
- FEATURE_DIR
- FEATURE_SPEC
- IMPL_PLAN
- TASKS
- AVAILABLE_DOCS

Abort with error if any required file is missing (instruct user to complete prerequisite workflows).
For single quotes in args like "I'm Groot", use escape syntax: e.g 'I'\''m Groot' (or double-quote if possible: "I'm Groot").

### 2. Validate Implementation Completeness

Check that implementation phase is complete:
- Read tasks.md and verify all tasks marked as [X] completed
- If incomplete tasks exist, WARN user and ask: "Implementation appears incomplete. Continue review anyway? (yes/no)"
- If user declines, abort with message to complete `/speckit.implement` first

### 3. Run Automated Quality Gate Checks

Execute `./scripts/quality-gate.sh` from repository root:

```bash
./scripts/quality-gate.sh
```

**Parse script output** and extract:
- Test execution status (PASS/FAIL)
- TODO/FIXME/HACK detection results
- Fake/mock implementation detection results
- Test coverage percentage and status
- Library-first approach warnings

**Severity mapping**:
- Any FAIL from quality-gate.sh → CRITICAL finding
- Any WARN from quality-gate.sh → MEDIUM finding
- All checks PASS → No automated findings

### 4. Re-run Constitution & Spec Validation

Execute internal `/speckit.analyze` logic (do NOT invoke as separate command - run the analysis inline):

- Load constitution from `.specify/memory/constitution.md`
- Load architecture patterns from `.specify/architecture-patterns.md`
- Validate spec.md, plan.md, tasks.md alignment
- Check for constitution violations
- Detect coverage gaps, ambiguities, inconsistencies
- Verify implementation follows established architecture patterns

**Severity mapping**:
- Constitution MUST violation → CRITICAL
- Architecture pattern violation (from architecture-patterns.md) → CRITICAL or MAJOR depending on impact
- Missing core requirement coverage → CRITICAL
- Conflicting requirements → HIGH (map to MAJOR for review)
- Terminology drift, missing non-functional coverage → MEDIUM
- Style/wording improvements → LOW

### 5. Architecture Integration Review

Scan implementation files to validate architecture patterns defined in Constitution Principles I-X:

**Principle I: Code Quality & DRY**
- Search for duplicated code patterns (similar function/method names, copy-paste signatures)
- Check against Architecture Pattern: Service Layer (business logic in services/, not API routes)
- Flag: Duplicated logic that should be extracted (MAJOR)
- Flag: Business logic in API routes instead of services (MAJOR)

**Principle II: Library-First Approach**
- Already checked by quality-gate.sh
- Review any warnings from automated check

**Principle III: Comprehensive Testing**
- Already checked by quality-gate.sh (coverage ≥80%)
- Verify test files follow AAA pattern (sample 5 random tests per architecture-patterns.md)
- Check test naming follows convention: `test_<action>_<condition>_<expected_result>`
- Flag: Tests without clear Arrange-Act-Assert structure (MEDIUM)
- Flag: Tests not following naming convention (LOW)

**Principle IV: UX Consistency**
- For CLI: Check flag naming consistency (`rg "click.option" src/bcd_cli/` - verify similar options use same naming conventions)
- For API: Check response schema consistency (`rg "class.*Schema" src/bcd_api/schemas/` - verify naming patterns)
- For Web: Check component naming consistency
- Flag: Inconsistent naming or UI patterns (MEDIUM)

**Principle VII: Database Schema Versioning**
- Check if models changed: `git diff main..HEAD -- src/bcd_api/models/`
- If models changed, verify Alembic migration exists: `ls -t migrations/versions/ | head -1`
- Flag: Model changes without migration (CRITICAL)

**Principle X: Internationalization**
- Search for hard-coded strings in production code:
  ```bash
  rg '"[A-Z][a-z]{3,}"' src/bcd_api/ src/bcd_cli/ src/bcd_web_vue/ --type py --type js | grep -v "test_" | grep -v "locales/"
  ```
- Flag: Hard-coded user-facing strings (MAJOR for UI/CLI, MEDIUM for API messages)

**Principle XI: Quality Gate Process**
- Verify this review process is being followed (self-validating)

### 6. Cross-Platform Compatibility Check

**File Path Handling**:
- Search for hard-coded path separators: `rg '"/.*/"' src/ --type py | grep -v "test_" | grep -v "http://"`
- Flag: Hard-coded "/" or "\\" instead of pathlib (MEDIUM)

**Platform-Specific Code**:
- Search for platform checks without fallback: `rg "sys.platform|platform.system" src/ --type py -A 3`
- Flag: Platform-specific code without cross-platform handling (MEDIUM)

### 7. Data Integrity & Backup Check

**Data Loss Prevention**:
- Check for database operations without transactions: `rg "session.commit|db.commit" src/bcd_api/ --type py`
- Verify critical operations (delete, bulk update) are wrapped in try/except
- Flag: Delete operations without confirmation or transaction handling (MAJOR)

**Backup & Recovery**:
- Verify backup functionality exists (search for backup endpoints/commands)
- Flag: No backup mechanism for library data (MAJOR - librarians need data protection)

### 8. Performance Review (Localhost/LAN Context)

**Context**: Single librarian or small team on local network. Performance targets: <100ms for common operations, <2s for reports on 5,000+ records.

**N+1 Query Pattern**:
- Search for loops with database queries: `rg "for .* in.*:\s*db\." src/bcd_api/ --type py -A 2`
- Flag: Potential N+1 queries affecting librarian workflow speed (MAJOR)

**Missing Pagination**:
- Search for endpoints returning lists: `rg "List\[.*\]" src/bcd_api/api/ --type py`
- Verify corresponding service methods use limit/offset
- Flag: Collection endpoints without pagination that could slow UI on large datasets (MAJOR)

**Barcode Scanner Responsiveness**:
- Check for synchronous operations during checkout/return flows
- Flag: Operations >200ms in checkout flow (MEDIUM - impacts librarian efficiency during busy periods)

**Database Indexing**:
- Verify indexes exist for common queries (borrower ID lookups, item barcode lookups, overdue searches)
- Flag: Missing indexes on frequently queried fields (MAJOR - affects librarian daily workflow)

### 9. Librarian UX & Workflow Review

**Barcode Scanner Support**:
- Verify input fields support Enter key submission (barcode scanners emit Enter)
- Check that focus management works for scanner workflow
- Flag: Forms requiring mouse clicks between scans (MAJOR - breaks scanner workflow)

**Error Recovery**:
- Verify librarians can retry failed operations without losing entered data
- Check that network errors to localhost API show clear retry options
- Flag: Data loss on API errors or unclear error messages (MAJOR)

**Offline/Network Handling**:
- Verify graceful handling when API server (localhost:8000) is not running
- Flag: Confusing errors when connecting to localhost API (MEDIUM)

**Print Functionality**:
- Check browser print compatibility for reports and labels
- Flag: Print layouts broken or missing (MEDIUM - librarians need to print overdue notices)

**Keyboard Navigation**:
- Verify common workflows completable via keyboard (important for efficiency)
- Flag: Essential actions requiring mouse clicks (MEDIUM)

### 10. Generate Review Report

Output a structured Markdown review report:

---

## Post-Implementation Review Report

**Feature**: [Feature name from spec.md]
**Feature ID**: [Feature branch/ID]
**Review Date**: [YYYY-MM-DD]
**Reviewer**: Claude AI Architect (Constitution-Aware)
**Deployment Context**: Localhost/LAN Elementary School Library Application

---

### Executive Summary

- **Total Findings**: [Count]
  - CRITICAL: [Count] 🔴
  - MAJOR: [Count] 🟠
  - MEDIUM: [Count] 🟡
  - LOW: [Count] ⚪

- **Merge Recommendation**:
  - ✅ **APPROVED** - Zero CRITICAL/MAJOR/MEDIUM findings
  - ⚠️ **APPROVED WITH CONDITIONS** - MEDIUM findings documented and accepted below
  - ❌ **BLOCKED** - CRITICAL or MAJOR findings must be resolved

---

### Automated Quality Gate Results

| Check | Status | Details |
|-------|--------|---------|
| All tests pass | ✅ PASS / ❌ FAIL | [Details from quality-gate.sh] |
| No TODO/FIXME/HACK | ✅ PASS / ❌ FAIL | [Details] |
| No fake/mock implementations | ✅ PASS / ❌ FAIL | [Details] |
| Coverage ≥80% | ✅ PASS / ❌ FAIL | [Coverage percentage] |
| Library-first approach | ✅ PASS / ⚠️ WARN | [Details] |

---

### Constitution Compliance Review

| Principle | Status | Findings |
|-----------|--------|----------|
| I. Code Quality & DRY | ✅ / ⚠️ / ❌ | [Details] |
| II. Library-First | ✅ / ⚠️ / ❌ | [Details] |
| III. Comprehensive Testing | ✅ / ⚠️ / ❌ | [Details] |
| IV. UX Consistency | ✅ / ⚠️ / ❌ | [Details] |
| V. Click Minimization | ✅ / ⚠️ / ❌ / N/A | [Details] |
| VI. Performance for Legacy Hardware | ✅ / ⚠️ / ❌ | [Details] |
| VII. Database Schema Versioning | ✅ / ⚠️ / ❌ | [Details] |
| VIII. Research-First | ✅ / ⚠️ / ❌ | [Details] |
| IX. Design-First | ✅ / ⚠️ / ❌ | [Details] |
| X. Internationalization | ✅ / ⚠️ / ❌ | [Details] |
| XI. Quality Gate Process | ✅ / ⚠️ / ❌ | [Meta-validation] |

---

### Findings Detail

| ID | Severity | Category | Location | Issue | Recommendation |
|----|----------|----------|----------|-------|----------------|
| F-001 | CRITICAL/MAJOR/MEDIUM/LOW | [Category] | [file:line] | [Description] | [Fix recommendation] |

*(Generate stable IDs prefixed by F-001, F-002, etc.)*

---

### Architecture Review

**Service Layer Pattern**: [Assessment]
**API Contracts**: [Assessment]
**Database Migrations**: [Assessment]
**Cross-Platform Compatibility**: [Assessment]
**Data Integrity & Backup**: [Assessment]
**Performance for Librarian Workflows**: [Assessment]

---

### Librarian UX Assessment

**Barcode Scanner Integration**: [Assessment]
**Keyboard Workflow Efficiency**: [Assessment]
**Error Recovery & Guidance**: [Assessment]
**Print Functionality**: [Assessment]
**Overall Usability for Non-Technical Users**: [Assessment]

---

### Spec/Plan/Implementation Alignment

- [ ] Implementation matches spec.md acceptance criteria
- [ ] Technical approach follows plan.md architecture
- [ ] All tasks.md items completed
- [ ] No deviation from approved design without documentation

**Alignment Issues** (if any):
[List any discrepancies between spec/plan and actual implementation]

---

### Localhost/LAN Deployment Notes

**Appropriate for Deployment Context**:
- Application designed for trusted local network use
- No authentication required (localhost single-user model)
- Performance optimized for single-user/small-team workflows
- Focus on data integrity and usability, not attack prevention

**Deployment Checklist**:
- [ ] Backup/restore functionality tested
- [ ] Works on school librarian computers (legacy hardware)
- [ ] Barcode scanner compatibility verified
- [ ] Print functionality tested on school printers
- [ ] French localization complete and tested
- [ ] Cross-platform tested (Linux server + Windows/Linux clients)

---

### Next Actions

**If CRITICAL or MAJOR findings exist**:
1. Fix all CRITICAL findings (blocks merge)
2. Fix all MAJOR findings (blocks merge)
3. Re-run `/speckit.review` after fixes
4. Do NOT merge until clean review

**If only MEDIUM findings exist**:
1. Document acceptance rationale for each MEDIUM finding OR fix them
2. Proceed to manual architect review if accepted
3. Merge after manual approval

**If only LOW findings exist or zero findings**:
1. ✅ Automated gates PASSED
2. Proceed to manual architect review (optional but recommended)
3. Safe to merge after any final review

---

### Review Checklist Export

Copy `.specify/quality-gate-checklist.md` to `specs/[feature-id]/quality-gate-review.md` and fill in:
- Paste this review report into "Automated Check Results" section
- Complete manual architect review sections
- Sign off when ready to merge

---

**Review Command**: `/speckit.review`
**Constitution Version**: [Version from constitution.md]
**Architecture Patterns**: `.specify/architecture-patterns.md` v1.0.0
**Quality Gate Script**: `./scripts/quality-gate.sh`
**Deployment Context**: Elementary School Library - Localhost/LAN

---

### 11. User Interaction

After generating the report:

**If CRITICAL or MAJOR findings**:
- Display findings table
- Output: "❌ **MERGE BLOCKED** - Fix CRITICAL and MAJOR findings, then re-run `/speckit.review`"
- Do NOT proceed to merge

**If only MEDIUM findings**:
- Display findings table
- Ask user: "Accept these MEDIUM findings and proceed? Document rationale: (yes with reason / no)"
- If user provides acceptance reason, add to report
- If user declines, recommend fixing findings

**If only LOW or zero findings**:
- Display summary
- Output: "✅ **REVIEW PASSED** - Safe to merge after optional manual architect review"
- Suggest: "Run `cp .specify/quality-gate-checklist.md specs/[feature-id]/quality-gate-review.md` to document review"

### 12. Save Review Report

Write review report to: `specs/[feature-id]/review-report-YYYY-MM-DD.md`

Notify user of saved location.

## Operating Principles

**Deterministic**: Running review multiple times on same code produces consistent results.

**Non-Destructive**: Never modifies implementation files, only generates review report.

**Constitution-First**: All 11 principles checked; violations automatically elevated to appropriate severity.

**Pattern-Based**: Validates against proven architecture patterns from `.specify/architecture-patterns.md` - ensures consistency with existing codebase.

**Context-Aware**: Standards calibrated for localhost/LAN school library deployment - focus on data integrity, usability, and performance, not security attacks.

**Actionable**: Every finding includes specific location and fix recommendation with reference to architecture patterns document.

**Merge-Focused**: Clear decision (APPROVED / APPROVED WITH CONDITIONS / BLOCKED) based on severity.

**Librarian-Centric**: UX and workflow checks prioritize librarian efficiency and barcode scanner integration.

## Context

$ARGUMENTS
