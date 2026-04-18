/**
 * Label sheet format configurations for barcode printing.
 *
 * All dimensions in millimetres. Formats are identified by their
 * label count per A4 sheet — no brand or model references in this file.
 *
 * Layout parameters:
 *   top_margin_mm   — distance from top of page to top of first row
 *   left_margin_mm  — distance from left of page to left of first column
 *   col_gap_mm      — horizontal gap between adjacent label columns
 *   row_gap_mm      — vertical gap between adjacent label rows
 */

export const LABEL_FORMATS = [
    {
        id: '48',
        labelsPerSheet: 48,
        recommended: false,
        label: { width_mm: 45.7, height_mm: 21.2 },
        layout: {
            cols: 4,
            rows: 12,
            top_margin_mm: 10.7,
            left_margin_mm: 9.9,
            col_gap_mm: 0.0,
            row_gap_mm: 0.0,
        },
    },
    {
        id: '27',
        labelsPerSheet: 27,
        recommended: false,
        label: { width_mm: 63.5, height_mm: 29.6 },
        layout: {
            cols: 3,
            rows: 9,
            top_margin_mm: 10.3,
            left_margin_mm: 7.2,
            col_gap_mm: 2.5,
            row_gap_mm: 3.1,
        },
    },
    {
        id: '24',
        labelsPerSheet: 24,
        recommended: false,
        label: { width_mm: 63.5, height_mm: 33.9 },
        layout: {
            cols: 3,
            rows: 8,
            top_margin_mm: 15.15,
            left_margin_mm: 7.22,
            col_gap_mm: 2.54,
            row_gap_mm: 0.0,
        },
    },
    {
        id: '21',
        labelsPerSheet: 21,
        recommended: true,
        label: { width_mm: 63.5, height_mm: 38.1 },
        layout: {
            cols: 3,
            rows: 7,
            top_margin_mm: 15.09,
            left_margin_mm: 7.22,
            col_gap_mm: 2.54,
            row_gap_mm: 0.0,
        },
    },
    {
        id: '18',
        labelsPerSheet: 18,
        recommended: false,
        label: { width_mm: 63.5, height_mm: 46.6 },
        layout: {
            cols: 3,
            rows: 6,
            top_margin_mm: 8.7,
            left_margin_mm: 7.22,
            col_gap_mm: 2.54,
            row_gap_mm: 0.0,
        },
    },
    {
        id: '16',
        labelsPerSheet: 16,
        recommended: false,
        label: { width_mm: 99.1, height_mm: 33.9 },
        layout: {
            cols: 2,
            rows: 8,
            top_margin_mm: 12.9,
            left_margin_mm: 4.67,
            col_gap_mm: 2.54,
            row_gap_mm: 0.0,
        },
    },
    {
        id: '14',
        labelsPerSheet: 14,
        recommended: false,
        label: { width_mm: 99.1, height_mm: 38.1 },
        layout: {
            cols: 2,
            rows: 7,
            top_margin_mm: 15.09,
            left_margin_mm: 4.67,
            col_gap_mm: 2.54,
            row_gap_mm: 0.0,
        },
    },
    {
        id: '12',
        labelsPerSheet: 12,
        recommended: true,
        label: { width_mm: 63.5, height_mm: 71.96 },
        layout: {
            cols: 3,
            rows: 4,
            top_margin_mm: 3.53,
            left_margin_mm: 7.35,
            col_gap_mm: 2.5,
            row_gap_mm: 0.0,
        },
    },
    {
        id: '8',
        labelsPerSheet: 8,
        recommended: false,
        label: { width_mm: 99.1, height_mm: 67.7 },
        layout: {
            cols: 2,
            rows: 4,
            top_margin_mm: 13.7,
            left_margin_mm: 4.67,
            col_gap_mm: 2.54,
            row_gap_mm: 0.0,
        },
    },
];

/** Default format: 21 labels per sheet (63.5 × 38.1 mm), recommended for BCD */
export const DEFAULT_FORMAT_ID = '21';
