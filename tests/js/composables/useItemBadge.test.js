import { describe, expect, it } from 'vitest';
import { ref } from 'vue';

import { useItemBadge } from '../../../src/bcd_web_vue/js/composables/useItemBadge.js';

describe('useItemBadge', () => {
    it('returns null for an absent shelf location or call number', () => {
        const badges = useItemBadge(ref({}));

        expect(badges.getShelfBadge(null)).toBeNull();
        expect(badges.getCoteBadge('')).toBeNull();
    });

    it('uses a readable colour for a configured shelf location', () => {
        const badges = useItemBadge(ref({
            catalog_shelf_locations: JSON.stringify([
                { label: 'Romans', color: '#ffffff' },
                { label: 'Albums', color: '#003366' }
            ])
        }));

        expect(badges.getShelfBadge('Romans')).toMatchObject({
            background: '#ffffff',
            color: '#000000',
            borderRadius: '4px'
        });
        expect(badges.getShelfBadge('Albums')).toMatchObject({
            background: '#003366',
            color: '#ffffff',
            borderRadius: '4px'
        });
    });

    it('renders unknown and uncoloured locations as neutral outlined badges', () => {
        const badges = useItemBadge(ref({
            catalog_shelf_locations: JSON.stringify([{ label: 'Reserve', color: null }])
        }));

        expect(badges.getShelfBadge('Reserve')).toMatchObject({
            background: 'transparent',
            border: '1px solid currentColor'
        });
        expect(badges.getShelfBadge('Unknown')).toMatchObject({
            background: 'transparent',
            border: '1px solid currentColor'
        });
    });

    it('maps a Dewey first digit to its configured call-number colour', () => {
        const badges = useItemBadge(ref({
            dewey_colors: JSON.stringify([
                '#ffffff', '#111111', '#222222', '#333333', '#444444',
                '#555555', '#666666', '#777777', '#888888', '#999999'
            ])
        }));

        expect(badges.getCoteBadge('  012.3 VER')).toMatchObject({
            background: '#ffffff',
            color: '#000000',
            outline: '1px solid #ddd',
            borderRadius: '20px'
        });
        expect(badges.getCoteBadge('812.4 HUG')).toMatchObject({
            background: '#888888',
            color: '#ffffff',
            outline: 'none'
        });
    });

    it('falls back safely when configured JSON is malformed or incomplete', () => {
        const badges = useItemBadge(ref({
            catalog_shelf_locations: '{invalid',
            dewey_colors: JSON.stringify(['#000000'])
        }));

        expect(badges.getShelfBadge('Romans')).toMatchObject({
            background: 'transparent',
            border: '1px solid currentColor'
        });
        expect(badges.getCoteBadge('100')).toMatchObject({
            background: 'transparent',
            border: '1px solid currentColor'
        });
    });
});
