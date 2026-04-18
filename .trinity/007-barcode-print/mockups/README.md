# Barcode Printing Mockups

This directory contains HTML mockups for the three barcode printing features.

## Files

### 1. `borrower-reference.html`
**Borrower Reference Sheets** - For librarian use

- **Purpose**: Reference guide showing all students grouped by class
- **Layout**: One class per page (A4)
- **Content**: Student ID, barcode, full name, status
- **Use case**: Librarian keeps these sheets to quickly find a student's barcode

**Preview**: Open in browser, shows 3 classes (CP-A, CE1-B, CE2-C) with multiple students each

### 2. `student-cards.html`
**Student Library Cards** - Individual cards for students

- **Purpose**: Physical cards for students to carry
- **Layout**: 10 cards per A4 page (2 columns × 5 rows)
- **Size**: 85mm × 54mm (standard card size)
- **Content**: Library name, student photo placeholder, name, ID, class, barcode
- **Use case**: Print on cardstock, cut out, give to students

**Preview**: Open in browser, shows 10 library cards ready to cut

### 3. `item-labels.html`
**Item Labels (Book Stickers)** - Avery-compatible labels

- **Purpose**: Stickers to attach to books
- **Layout**: 12 labels per page (3 columns × 4 rows)
- **Size**: 66mm × 25mm (Avery 5160/6479 compatible)
- **Content**: Barcode, item ID, library name
- **Use case**: Print on Avery label sheets, apply to books

**Preview**: Open in browser, shows 24 labels (2 pages) in 3×4 grid

## How to View

### Option 1: Browser (Recommended)
```bash
# Open any mockup in your default browser
firefox ~/.trinity/0007-barcode-print/mockups/borrower-reference.html
firefox ~/.trinity/0007-barcode-print/mockups/student-cards.html
firefox ~/.trinity/0007-barcode-print/mockups/item-labels.html
```

### Option 2: Simple HTTP Server
```bash
cd ~/.trinity/0007-barcode-print/mockups/
python -m http.server 8080

# Then open in browser:
# http://localhost:8080/borrower-reference.html
# http://localhost:8080/student-cards.html
# http://localhost:8080/item-labels.html
```

## Features

✅ **Working barcodes** - Uses JsBarcode (CDN) to generate CODE39 barcodes
✅ **Print-ready** - Press Ctrl+P to see print preview
✅ **Responsive layouts** - Grid-based CSS for precise alignment
✅ **Sample data** - Realistic French student names and IDs
✅ **Print CSS** - Hides buttons and info banners when printing
✅ **Page breaks** - Each class on new page (borrower reference)

## Print Testing

1. **Open mockup** in Chrome/Firefox
2. **Press Ctrl+P** (or Cmd+P on Mac)
3. **Verify layout** in print preview
4. **Adjust margins** if needed (use browser's print settings)
5. **Print test page** to verify barcode scanner compatibility

## Notes

- **Barcodes are scannable** - Test with actual barcode scanner
- **Avery compatibility** - Item labels align with Avery 5160/6479 sheets
- **Card stock** - Student cards print best on 200-300g cardstock
- **Cutting guides** - Dashed borders on screen (removed when printing)

## Next Steps

These mockups demonstrate the final layout. The Vue.js implementation will:
- Fetch real data from API endpoints
- Generate barcodes client-side using JsBarcode
- Use the same CSS layouts as these mockups
- Add filtering (by class, date range, etc.)

## Adjustments

If layouts need tweaking:
- **Font sizes**: Edit `.borrower-id`, `.card-name`, `.label-id` in CSS
- **Grid spacing**: Adjust `gap` in `.card-grid` or `.label-grid`
- **Page margins**: Modify `@page { margin: ... }` in CSS
- **Barcode dimensions**: Change `width`, `height` in JsBarcode options
