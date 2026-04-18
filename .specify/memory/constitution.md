<!--
Sync Impact Report:
Version Change: 1.1.0 → 1.2.0
Type: MINOR - New principle added (Quality Gate Process)
Modified Principles:
  - None
Added Principles:
  - XI. Quality Gate Process
Removed Principles:
  - None
Added Sections:
  - Quality Gate Process standards
Templates Requiring Updates:
  ✅ .specify/templates/plan-template.md - Constitution Check section already present
  ✅ .specify/templates/spec-template.md - Aligns with user scenario focus and requirements
  ✅ .specify/templates/tasks-template.md - Task organization supports principles
Follow-up TODOs:
  - Created scripts/quality-gate.sh for automated validation
  - Created .specify/quality-gate-checklist.md template
-->

# BCD3 Project Constitution

## Core Principles

### I. Code Quality & DRY (Don't Repeat Yourself)

Code MUST be written with clarity, maintainability, and reusability as primary objectives.
Duplication is a violation unless explicitly justified.

**Rules:**
- Duplicated logic MUST be extracted into reusable functions, classes, or modules after
  the second occurrence
- Shared constants, configuration, and validation rules MUST be centralized in single
  source files
- Copy-paste programming is prohibited; similar code patterns MUST be abstracted
- Magic numbers and hard-coded values MUST be replaced with named constants
- Code reviews MUST reject PRs with unjustified duplication

**Rationale:** DRY reduces bugs (fix once, not everywhere), accelerates feature
development, and ensures consistency. Technical debt from duplication compounds
exponentially over time.

### II. Library-First Approach

Leverage existing, well-maintained libraries instead of reinventing solutions. Custom
implementations are only justified when libraries add more complexity than value.

**Rules:**
- MUST use established libraries for common problems (date/time, HTTP, validation,
  parsing, etc.)
- Library adoption criteria:
  - Reduces total lines of code by ≥30% compared to custom implementation
  - Improves code clarity and readability
  - Actively maintained (updated within last 6 months)
  - Well-documented with clear API
  - Reasonable dependency footprint
  - Cross-platform compatible (Linux & Windows)
- Custom implementations MUST be justified in writing with:
  - Why existing libraries are inadequate
  - Complexity/performance tradeoffs
  - Long-term maintenance plan
- Avoid micro-dependencies (libraries that could be replaced by 5-10 lines of clear code)
- Regularly audit dependencies for security, maintenance status, and necessity

**Rationale:** Libraries encapsulate best practices, are battle-tested across many use
cases, receive security updates, and free developers to focus on business logic. Time
spent maintaining custom implementations of solved problems is wasted.

### III. Comprehensive Testing Standards

Testing is NON-NEGOTIABLE. All code changes MUST include appropriate test coverage
before merge.

**Rules:**
- **Unit Tests MUST**:
  - Cover all public functions and methods
  - Test edge cases, boundary conditions, and error paths
  - Execute in isolation (no external dependencies)
  - Run in under 100ms per test
- **Integration Tests MUST**:
  - Verify component interactions and data flow
  - Test critical user journeys end-to-end
  - Cover API contracts and external service integrations
  - Test on both Linux and Windows platforms
- **Test-First Development**:
  - For new features: Write failing tests → Get approval → Implement → Pass tests
  - For bug fixes: Write test that reproduces bug → Fix → Verify test passes
- **Coverage Requirements**:
  - Minimum 80% line coverage for new code
  - 100% coverage for critical security and data integrity paths
- **Test Quality**:
  - Tests MUST be deterministic (no flaky tests)
  - Test names MUST clearly describe what is being tested
  - Failed tests MUST block deployment

**Rationale:** Comprehensive testing prevents regressions, enables confident refactoring,
documents expected behavior, and reduces production incidents.

### IV. User Experience Consistency

User interfaces and interactions MUST maintain consistency across the entire application
to reduce cognitive load.

**Rules:**
- **Visual Consistency**:
  - Use a single design system/component library
  - Consistent spacing, typography, colors, and iconography
  - Same UI patterns for similar actions (e.g., all delete actions use same confirmation)
- **Behavioral Consistency**:
  - Keyboard shortcuts MUST be consistent across features
  - Form validation MUST follow same rules and display patterns
  - Error messages MUST follow consistent structure and tone
  - Loading/progress indicators MUST use consistent patterns
- **Navigation Consistency**:
  - Navigation patterns MUST be predictable (same menu structure, breadcrumbs)
  - Back/cancel actions MUST behave intuitively
  - Context preservation across navigation
- **CLI Consistency** (for command-line interfaces):
  - Flag naming conventions MUST be consistent (e.g., -v/--verbose, -h/--help)
  - Output format MUST be consistent (structured data, error reporting)
  - Exit codes MUST follow conventions (0 = success, non-zero = error)
- **Accessibility**:
  - Labels MUST be consistent for similar elements
  - Focus management MUST follow predictable patterns
  - Color contrast ratios MUST meet WCAG 2.1 AA standards

**Rationale:** Consistency reduces learning curve, minimizes user errors, builds user
confidence, and improves accessibility. Users transfer knowledge from one feature to
another seamlessly.

### V. Click Minimization

Every user action MUST be evaluated for necessity. Unnecessary interactions are friction
that degrades user experience.

**Rules:**
- **Direct Actions**:
  - Primary actions MUST be accessible in ≤2 steps from main entry point
  - Common workflows MUST NOT require more than 3 interactions to complete
  - Inline editing MUST be preferred over dialog-based editing when feasible
- **Smart Defaults**:
  - Forms/prompts MUST pre-populate with sensible defaults when context is available
  - Previous user choices MUST be remembered and suggested
  - Required inputs MUST be minimized; only ask for essential information
- **Batch Operations**:
  - Repetitive actions MUST support bulk/batch operations
  - Multi-select MUST be available for list operations
- **Keyboard Navigation**:
  - All workflows MUST be completable via keyboard alone
  - Power users MUST have shortcuts for frequent actions
- **Auto-save/Auto-commit**:
  - Progress SHOULD be saved automatically when possible
  - Explicit confirmation only when transaction boundaries require it

**Rationale:** Each unnecessary interaction is an opportunity for user frustration and
abandonment. Reducing interactions increases task completion rates and user satisfaction.

### VI. Performance for Legacy Hardware

Applications MUST remain responsive and functional on older, resource-constrained devices
(5+ year old computers).

**Rules:**
- **Target Hardware Baseline**:
  - Dual-core CPU (2.0 GHz)
  - 4GB RAM
  - HDD storage (not SSD)
  - Integrated graphics
- **Performance Budgets**:
  - Application startup: ≤3 seconds on legacy hardware
  - Time to Interactive: ≤5 seconds
  - Runtime: Smooth animations (60fps where applicable), ≤100ms response to user input
  - Memory footprint: ≤200MB for CLI tools, ≤500MB for GUI applications
- **Optimization Requirements**:
  - Code MUST be optimized for startup time (lazy loading, deferred initialization)
  - Assets (images, fonts, data files) MUST be compressed and optimized
  - Database queries MUST be indexed and optimized (no N+1 queries)
  - Expensive computations MUST be debounced, throttled, cached, or moved to background
    workers
  - Large datasets MUST be paginated server-side (never load entire dataset into memory)
- **Graceful Degradation**:
  - Core functionality MUST work with minimal resources
  - Progressive enhancement over graceful degradation
  - Features MUST degrade gracefully on resource-constrained systems
- **Monitoring**:
  - Performance metrics MUST be tracked in production
  - Real User Monitoring (RUM) data MUST inform optimization priorities

**Rationale:** Performance is a feature, not a luxury. Excluding users with older
hardware creates accessibility barriers and limits market reach. Fast applications feel
more reliable and professional.

### VII. Database Schema Versioning & Migrations

Database schemas MUST be version-controlled with explicit migration paths to enable safe,
reversible changes.

**Rules:**
- **Schema Versioning**:
  - All schema changes MUST be defined in versioned migration files
  - Migration files MUST be sequential and never modified after merge
  - Each migration MUST include both upgrade (up) and downgrade (down) scripts
  - Migration version MUST be stored in the database
- **Migration Requirements**:
  - Migrations MUST be idempotent (safe to run multiple times)
  - Data transformations MUST preserve data integrity
  - Migrations MUST be tested with production-like data volumes
  - Breaking changes MUST include transition period with backward compatibility
- **Sample Data First**:
  - Sample/seed data MUST be defined BEFORE finalizing schema design
  - Sample data MUST represent realistic production scenarios (edge cases, volumes)
  - Schema design MUST be validated against sample data requirements
  - Test suite MUST use sample data for integration tests
- **Pagination**:
  - All queries returning collections MUST support server-side pagination
  - Default page size MUST be reasonable (≤100 records)
  - Pagination MUST use cursor-based or offset-based approach consistently
  - Total count queries MUST be optional/cacheable (expensive on large datasets)

**Rationale:** Versioned migrations enable safe, trackable database evolution. Sample data
first ensures schema designs meet real-world needs. Server-side pagination prevents
out-of-memory errors and ensures scalability.

### VIII. Research-First Feature Design

Before designing any feature specification, MUST research existing solutions and best
practices to avoid reinventing the wheel poorly.

**Rules:**
- **Pre-Design Research**:
  - MUST search for similar existing software and analyze their approaches
  - MUST review documentation, user guides, and API designs of comparable tools
  - MUST identify common patterns, conventions, and user expectations
  - MUST document findings and key learnings in research phase
- **Research Artifacts**:
  - Create research.md documenting similar tools, their approaches, pros/cons
  - Include links to relevant documentation, tutorials, API references
  - Identify which patterns to adopt vs. improve upon
  - Note user pain points from existing solutions to avoid
- **Learning from Others**:
  - Borrow proven UX patterns from successful tools
  - Adopt established conventions (file formats, CLI flags, config structures)
  - Learn from others' mistakes (known issues, design flaws, user complaints)
  - Understand ecosystem expectations (interoperability, standards)

**Rationale:** Most problems have been solved before. Research prevents wasted effort on
inferior solutions, leverages collective wisdom, and ensures designs align with user
expectations formed by existing tools.

### IX. Design-First Implementation

All features with user-facing interfaces MUST have mockups and design artifacts approved
before implementation begins.

**Rules:**
- **Mockup Requirements**:
  - CLI tools: MUST define command structure, flags, output formats, error messages
  - GUI applications: MUST provide wireframes or mockups for all screens/dialogs
  - APIs: MUST define request/response contracts with examples
  - All interactions: MUST define user flows with state transitions
- **Design Approval Gate**:
  - Mockups MUST be reviewed and approved by stakeholders before coding
  - Design changes discovered during implementation MUST be documented
  - Major design deviations MUST trigger re-review
- **Design Documentation**:
  - Visual mockups (wireframes, screenshots, or text-based layouts)
  - Interaction flows (state diagrams, user journey maps)
  - Sample inputs and outputs
  - Error handling and edge cases visualization
- **Implementation Alignment**:
  - Implementation MUST match approved designs
  - Deviations MUST be justified and documented

**Rationale:** Design-first prevents costly rework, ensures stakeholder alignment,
facilitates early feedback, and allows implementation to focus on correctness rather than
design decisions.

### X. Internationalization (i18n)

All user-facing text MUST be internationalized to support multiple languages. English and
French are the minimum required languages.

**Rules:**
- **No Hard-Coded Strings**:
  - All user-facing text MUST be externalized to translation files
  - Code MUST NOT contain hard-coded strings in any specific language
  - Translation keys MUST be descriptive and hierarchical (e.g., "errors.login.invalid_password")
- **Minimum Language Support**:
  - English (en) is the primary language and MUST be complete
  - French (fr) MUST be fully supported with professional translations
  - Additional languages MAY be added but en/fr are mandatory
- **Translation Infrastructure**:
  - Use established i18n libraries appropriate for the platform
  - Translation files MUST be in standard format (JSON, YAML, gettext .po, etc.)
  - Missing translations MUST fall back to English
  - Translation keys MUST be validated in CI (no missing keys)
- **Locale-Aware Formatting**:
  - Dates, times, and numbers MUST be formatted according to user's locale
  - Currency MUST be displayed according to locale conventions
  - Pluralization rules MUST respect language-specific rules
  - Text direction (LTR/RTL) MUST be considered for future languages
- **Translation Workflow**:
  - New features MUST include translations for both English and French
  - Translation files MUST be updated in same PR as feature code
  - PRs with missing translations MUST be blocked
  - Translation quality MUST be verified by native speakers when possible
- **Context for Translators**:
  - Translation keys SHOULD include context comments
  - Screenshots or mockups SHOULD accompany new strings
  - Character length constraints MUST be documented (UI space limitations)
- **Testing**:
  - Tests MUST run in both English and French locales
  - UI tests MUST verify text doesn't overflow containers in both languages
  - Language switching MUST be tested (if applicable)

**Rationale:** Internationalization from the start is far easier than retrofitting later.
Supporting English and French ensures accessibility for both anglophone and francophone
users, expanding market reach and inclusivity.

### XI. Quality Gate Process

Every feature MUST pass validation gates at two checkpoints to ensure consistent quality,
constitution compliance, and architectural integrity before merge.

**Rules:**

**Pre-Implementation Gate (Before /speckit.implement):**
- `/speckit.analyze` MUST show zero CRITICAL issues
- Constitution violations MUST be resolved before proceeding
- All ambiguities MUST be clarified via `/speckit.clarify`

**Post-Implementation Gate (Before merge):**

1. **Automated Validation**:
   - All tests pass (unit, integration, e2e)
   - Zero TODO/FIXME/HACK or fake/mock comments in production code
   - Test coverage ≥80% for new code
   - No custom implementations where libraries exist (validate against Principle #2)

2. **Constitution Re-Validation**:
   - Re-run `/speckit.analyze` to verify implementation alignment
   - Zero CRITICAL findings
   - Zero MAJOR findings
   - MEDIUM findings documented and accepted

3. **Architecture Review**:
   - Claude AI architect review required
   - Severity classification: CRITICAL/MAJOR/MEDIUM/LOW
   - MEDIUM or higher findings MUST block merge

**Severity Definitions:**
- **CRITICAL**: Core functionality broken, security vulnerability, constitution MUST violation,
  missing core requirement, blocks baseline functionality
- **MAJOR**: Logic errors, memory leaks, bad design choices, architectural duplication,
  untestable acceptance criteria, conflicting requirements
- **MEDIUM**: Readability issues, maintainability concerns, documentation gaps, terminology
  drift, missing non-functional task coverage, underspecified edge cases
- **LOW**: Style improvements, naming conventions, minor redundancy, optional suggestions

**Rationale:** Review at phase gates (not during implementation) reduces context switching
and produces 8x better results than unstructured approaches. Quality gates prevent
low-quality work from advancing and ensure constitution compliance. Research shows that
AI-assisted code has 3x more vulnerabilities than traditional code, making post-implementation
validation essential. The two-gate approach catches issues early (pre-implementation) and
validates execution quality (post-implementation) before merge.

## Internationalization Standards

**Supported Languages:**
- English (en) - Primary language, complete coverage required
- French (fr) - Full coverage required
- Additional languages may be added in future

**Translation File Structure:**
- Organized by feature/module for maintainability
- Hierarchical keys (dot notation or nested structure)
- One file per language per module (e.g., `auth.en.json`, `auth.fr.json`)

**Quality Standards:**
- Professional translations (not machine-translated)
- Consistent terminology across application
- Natural, idiomatic language (not literal word-for-word)
- Cultural appropriateness (date formats, examples, metaphors)

**Locale Support:**
- Date/time formatting: Use locale-aware libraries
- Number formatting: Respect decimal separators (. vs ,)
- Currency: Support both $ and € with proper formatting
- Collation: Sort strings according to locale rules

## Cross-Platform Requirements

**Supported Platforms:**
- Linux (primary development and deployment platform)
- Windows (must be fully functional)

**Platform Compatibility Rules:**
- File paths MUST use platform-agnostic path handling (e.g., pathlib in Python,
  path.join in Node.js)
- Line endings MUST be handled correctly (LF on Linux, CRLF on Windows)
- Environment variables and configuration MUST work on both platforms
- Shell commands MUST be abstracted or have platform-specific implementations
- Testing MUST include CI runs on both Linux and Windows
- Installation/setup documentation MUST cover both platforms

## Database Standards

**Query Performance:**
- All queries MUST have appropriate indexes for frequent access patterns
- Query plans MUST be reviewed for queries on large tables
- N+1 query patterns are PROHIBITED (use joins or batching)

**Pagination:**
- Server-side pagination is MANDATORY for all collection endpoints/queries
- Default page size: 50 records (configurable, maximum 100)
- Support both offset-based and cursor-based pagination where appropriate
- Provide total count only when explicitly requested (avoid expensive COUNT(*) queries)

**Data Integrity:**
- Foreign key constraints MUST be defined in schema
- Nullable vs. non-nullable MUST be explicitly defined
- Default values MUST be set at database level when appropriate
- Transactions MUST be used for multi-statement operations

## Performance Standards

**Startup & Response Times:**
- Application cold start: ≤3 seconds on legacy hardware
- Application warm start: ≤1 second
- Command execution / page navigation: ≤500ms
- Interactive response to user input: ≤100ms

**Runtime Performance:**
- Long-running operations (>2 seconds) MUST show progress indicators
- Blocking operations MUST be minimized (≤50ms)
- Animations/visual feedback: 60fps target (16.67ms per frame)
- API/query response time: p95 ≤200ms, p99 ≤500ms

**Resource Constraints:**
- Memory: Heap growth ≤10MB per hour of usage
- CPU: Idle time ≥80% when not processing
- Disk I/O: Minimize reads/writes, use buffering for bulk operations

**Testing Requirements:**
- Performance tests MUST be included in CI/CD pipeline
- Performance regressions >10% MUST block deployment
- Regular performance audits on target hardware

## Development Workflow

**Code Review Process:**
- All code MUST be peer-reviewed before merge
- Reviewers MUST verify:
  - Constitution compliance (all principles)
  - Test coverage and quality
  - No duplicated code
  - Appropriate library usage vs. custom implementation
  - Performance implications
  - UX consistency
  - Cross-platform compatibility
  - Internationalization (translations present for en/fr)
  - Database migrations (if applicable)
- PRs MUST include:
  - Description of changes and rationale
  - Screenshots/mockups for UI changes
  - Performance impact assessment for significant changes
  - Justification for new dependencies
  - Translation files for user-facing text (en/fr)
  - Migration plan for schema changes
  - Link to related issue/ticket

**Quality Gates:**
- Automated tests MUST pass on both Linux and Windows (unit, integration, e2e)
- Code coverage MUST meet minimums (80% for new code)
- Linting and formatting MUST pass
- Performance budgets MUST not be exceeded
- Security scans MUST show no critical vulnerabilities
- Database migrations MUST include up/down scripts and be tested
- Translation completeness MUST be validated (no missing keys in en/fr)
- Dependency audit MUST show no high/critical vulnerabilities

**Feature Development Workflow:**
1. **Research Phase**: Document similar tools and best practices
2. **Design Phase**: Create mockups and get approval, identify translatable strings
3. **i18n Phase**: Create translation files for en/fr
4. **Data Phase**: Define sample data before schema
5. **Schema Phase**: Create versioned migrations
6. **Test Phase**: Write failing tests (including i18n tests)
7. **Implementation Phase**: Make tests pass
8. **Validation Phase**: Cross-platform and multi-language testing

**Branching Strategy:**
- Feature branches created from main/master
- Branch naming: `[issue-number]-brief-description`
- Commit messages: Conventional Commits format (feat:, fix:, docs:, etc.)
- Squash merges preferred for cleaner history

**Deployment:**
- Staging environment MUST mirror production
- All changes MUST be validated in staging before production
- Database migrations MUST be tested in staging
- Rollback plan MUST be documented for schema changes
- Feature flags SHOULD be used for risky changes

## Governance

**Authority:**
This constitution supersedes all other coding practices, guidelines, and conventions.
When conflicts arise, this document takes precedence.

**Amendment Process:**
- Proposed changes MUST be documented with:
  - Rationale for change
  - Impact analysis on existing code and practices
  - Migration plan if breaking existing conventions
- Amendments require:
  - Team discussion and consensus
  - Documentation update
  - Communication to all contributors
- Constitution version MUST be incremented according to semantic versioning

**Compliance:**
- All PRs MUST be verified for constitution compliance during review
- Complexity and exceptions MUST be justified in writing
- Technical debt that violates principles MUST be tracked and prioritized for remediation
- Systematic violations indicate need for tooling/automation or constitution amendment

**Version Control:**
- Constitution changes are tracked in git with detailed commit messages
- Major changes require migration guides for existing code
- Version history provides context for evolution of project standards

**Enforcement:**
- Automated tooling SHOULD enforce rules where possible (linters, formatters, test
  coverage tools, migration validators)
- Code review checklist MUST include constitution verification
- Retrospectives SHOULD evaluate constitution effectiveness and identify improvement
  opportunities

**Version**: 1.2.0 | **Ratified**: 2026-01-30 | **Last Amended**: 2026-02-06
