# UI Mockups - Import/Export Feature

This directory contains interactive HTML mockups for the import/export feature. Open these files directly in your browser to see the visual design.

## Mockup Files

### 1. Export Dialog (`export-dialog.html`)

**Preview**: Catalog export dialog with format selection and filters

**Features shown**:
- Format selection dropdown (Standard BCD, BCDI, Dublin Core)
- Medium type filter with checkboxes
- Dewey decimal range filter
- Available-only filter
- Format-specific information display
- Clean modal design with proper spacing

**Key design patterns**:
- Modal overlay with centered content
- Form controls with proper labels
- Checkbox groups in grid layout
- Range inputs with visual separator
- Primary/secondary button hierarchy
- Context-sensitive help text

---

### 2. Import Wizard (`import-wizard.html`)

**Preview**: Multi-step import wizard (4 steps: Upload → Map → Preview → Confirm)

**Features shown**:

**Step 1 - Upload**:
- Drag-and-drop file upload area
- File selection with size/row count display
- Upload button with loading state

**Step 2 - Column Mapping**:
- Auto-detection summary (format, encoding, row count)
- Mapping table with confidence scores
- Color-coded confidence badges (high/medium/low)
- Dropdown for manual mapping correction
- Medium type normalization preview

**Step 3 - Preview**:
- Validation summary with badge counts (valid/warnings/errors)
- Preview table showing first 10 rows
- Error list with row numbers and messages
- Success confirmation with import count

**Interactive features**:
- Click step buttons to navigate between steps
- Visual step progress indicator
- Context-aware navigation buttons
- Completed steps marked with checkmarks

**Key design patterns**:
- Step progress bar with numbered circles
- Active/completed state indicators
- Large data tables with scrolling
- Color-coded validation badges
- Error highlighting in preview table
- Multi-step wizard navigation

---

### 3. Admin Medium Types (`admin-medium-types.html`)

**Preview**: Settings page for managing medium types and import mappings

**Features shown**:

**Medium Types Table**:
- System default types (with badge)
- Custom user-created types (highlighted)
- Active/inactive status badges
- Usage count (number of documents)
- Inline edit capability
- Deactivate/Delete/Reactivate actions
- Disabled delete for types in use

**Import Mappings Table**:
- External value → internal code mappings
- Source format badges (BCDI, Dublin Core, Custom)
- Filter controls (by type and format)
- Scrollable table for large datasets
- Quick delete action

**Modals**:
- Create medium type modal with validation hints
- Create mapping modal with dropdowns
- Form validation patterns
- Clear cancel/submit actions

**Key design patterns**:
- Settings page with tab navigation
- Admin tables with action columns
- Badge system for status/category
- Inline editing vs modal editing
- Disabled states for protected actions
- Filter controls above tables
- Empty state handling

---

## Design System

### Colors

- **Primary**: `#4CAF50` (green) - Primary actions, active states
- **Secondary**: `#f5f5f5` (light gray) - Secondary actions, backgrounds
- **Danger**: `#f44336` (red) - Delete actions, errors
- **Warning**: `#ff9800` (orange) - Deactivate actions, warnings
- **Success**: `#4CAF50` (green) - Success messages, valid states
- **Info**: `#2196F3` (blue) - Information, format detection

### Typography

- **Font family**: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto` (system fonts)
- **Headings**: 600 weight
- **Body**: 400 weight (14px base)
- **Small text**: 12-13px for hints and labels

### Spacing

- **Modal padding**: 24px body, 20px header/footer
- **Table padding**: 12px cells
- **Form groups**: 20px margin-bottom
- **Button gaps**: 12px between buttons

### Components

- **Buttons**: 10px vertical, 20px horizontal padding, 4px border-radius
- **Inputs**: 10px vertical, 12px horizontal padding, 1px border
- **Badges**: 4-6px vertical, 8-12px horizontal, 12px border-radius
- **Modals**: 8px border-radius, 0-4-20px box-shadow
- **Tables**: 1px borders, hover states on rows

### Accessibility

- **Focus states**: Green border with subtle shadow
- **Hover states**: Lighter background on buttons
- **Disabled states**: 50% opacity, no-pointer cursor
- **Color contrast**: WCAG AA compliant text colors
- **Labels**: All form inputs have visible labels
- **Close buttons**: Large click targets (28-32px)

---

## Usage in Development

1. **Reference for Vue components**: Use these mockups as visual reference when building Vue 3 components in `src/bcd_web_vue/js/components/`

2. **CSS extraction**: Extract styles into shared CSS files or component-specific styles

3. **Responsive design**: These mockups are desktop-first; add media queries for mobile/tablet

4. **i18n integration**: Replace French text with `i18n.t()` calls when implementing

5. **Vue bindings**: Replace static content with Vue reactive data (v-model, v-for, @click)

6. **API integration**: Connect modal actions to actual API endpoints from contracts/

---

## Browser Compatibility

These mockups use standard HTML/CSS and should work in:
- Chrome 90+ ✅
- Firefox 88+ ✅
- Safari 14+ ✅
- Edge 90+ ✅

No JavaScript frameworks required for the mockups themselves (vanilla JS only).

---

## Next Steps

1. **Review mockups** with stakeholders for design approval
2. **Implement Vue components** following the mockup structure
3. **Add real data** from API endpoints
4. **Test accessibility** with screen readers and keyboard navigation
5. **Responsive testing** on mobile/tablet devices

---

**Created**: 2026-02-06
**Feature**: 004-import-export
**Status**: Design mockups ready for implementation
