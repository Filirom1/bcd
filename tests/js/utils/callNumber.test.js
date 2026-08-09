import { describe, expect, it } from 'vitest';

import {
    computeAut1,
    computeAut3,
    stripLeadingArticles,
    computeSer1,
    computeSer3,
    computeTit1,
    computeTit3,
    suggestShelfLocation,
    matchWildcard,
    computeCallNumber
} from '../../../src/bcd_web_vue/js/utils/callNumber.js';

describe('Call Number Generation Utilities', () => {
    describe('computeAut1', () => {
        it('returns empty string when no authors are provided', () => {
            expect(computeAut1([])).toBe('');
            expect(computeAut1(null)).toBe('');
        });

        it('returns first uppercase letter of author last name (no accents)', () => {
            expect(computeAut1(['Antoine de Saint-Exupéry'])).toBe('S');
            expect(computeAut1(['Hébert, Jean-Marc'])).toBe('H');
            expect(computeAut1(['Marcel Pagnol'])).toBe('P');
        });
    });

    describe('computeAut3', () => {
        it('returns empty string when no authors are provided', () => {
            expect(computeAut3([])).toBe('');
        });

        it('returns first 3 uppercase letters of author last name', () => {
            expect(computeAut3(['Antoine de Saint-Exupéry'])).toBe('SAI');
            expect(computeAut3(['Hébert, Jean-Marc'])).toBe('HEB');
            expect(computeAut3(['Marcel Pagnol'])).toBe('PAG');
        });
    });

    describe('stripLeadingArticles', () => {
        it('strips French and English articles', () => {
            expect(stripLeadingArticles('Le Petit Prince')).toBe('Petit Prince');
            expect(stripLeadingArticles('La gloire de mon père')).toBe('gloire de mon père');
            expect(stripLeadingArticles("L'Étranger")).toBe('Étranger');
            expect(stripLeadingArticles('The Hobbit')).toBe('Hobbit');
            expect(stripLeadingArticles('An Elephant')).toBe('Elephant');
        });

        it('leaves non-article prefixes intact', () => {
            expect(stripLeadingArticles('Petite')).toBe('Petite');
        });
    });

    describe('computeSer1 and computeSer3', () => {
        it('returns fallbacks when collection is empty', () => {
            expect(computeSer1('', 'A')).toBe('A');
            expect(computeSer3('', 'AUT')).toBe('AUT');
        });

        it('returns clean series characters', () => {
            expect(computeSer1('La Bibliothèque Rose', 'A')).toBe('B');
            expect(computeSer3('La Bibliothèque Rose', 'AUT')).toBe('BIB');
        });
    });

    describe('computeTit1 and computeTit3', () => {
        it('returns first letter/letters of title stripping articles', () => {
            expect(computeTit1('Le Petit Prince')).toBe('P');
            expect(computeTit3('Le Petit Prince')).toBe('PET');
        });
    });

    describe('suggestShelfLocation', () => {
        it('suggests matching shelf location', () => {
            const locations = [
                { label: 'Documentaires' },
                { label: 'Romans' }
            ];
            expect(suggestShelfLocation('Roman', locations)).toBe('Romans');
            expect(suggestShelfLocation('Documentaire', locations)).toBe('Documentaires');
        });
    });

    describe('matchWildcard', () => {
        it('matches simple strings and wildcards', () => {
            expect(matchWildcard('Documentaire', 'Doc*')).toBe(true);
            expect(matchWildcard('Documentaire', '*taire')).toBe(true);
            expect(matchWildcard('Documentaire', '*ment*')).toBe(true);
            expect(matchWildcard('Roman', 'Roman')).toBe(true);
            expect(matchWildcard('Roman', 'BD')).toBe(false);
        });
    });

    describe('computeCallNumber', () => {
        it('uses default aut3 if no rules match', () => {
            const record = {
                title: 'Le Petit Prince',
                authors: ['Antoine de Saint-Exupéry']
            };
            expect(computeCallNumber(record, '', [])).toBe('SAI');
        });

        it('replaces pattern tokens correctly', () => {
            const record = {
                title: 'La gloire de mon père',
                authors: ['Marcel Pagnol'],
                collection: 'La Bibliothèque Rose',
                deweyNumber: '840',
                mediumType: 'Book'
            };
            const rules = [
                { medium_type: 'Book', pattern: '{DEWEY} {SER3} {TIT1}' }
            ];
            expect(computeCallNumber(record, '', rules)).toBe('840 BIB G');
        });
    });
});
