import { describe, expect, it } from 'vitest';
import { mount } from '@vue/test-utils';

import BreakdownPanel from '../../../../src/bcd_web_vue/js/components/reports/BreakdownPanel.js';
import PubYearPanel from '../../../../src/bcd_web_vue/js/components/reports/PubYearPanel.js';
import TauxRotationPanel from '../../../../src/bcd_web_vue/js/components/reports/TauxRotationPanel.js';

const currentYear = new Date().getFullYear();

describe('BreakdownPanel', () => {
    it('scales bars, resolves labels and emits a toggle', async () => {
        const wrapper = mount(BreakdownPanel, {
            props: {
                title: 'By support',
                subtitle: 'Click to filter',
                rows: [{ value: 'Book', count: 4 }, { value: 'Magazine', count: 2 }],
                activeValue: 'Book',
                labelFn: value => `label:${value}`,
                colorFn: (row, index) => `${row.value}:${index}`
            }
        });

        expect(wrapper.vm.max).toBe(4);
        expect(wrapper.vm.label('Book')).toBe('label:Book');
        expect(wrapper.vm.color({ value: 'Magazine', count: 2 }, 1)).toBe('Magazine:1');
        const firstRow = wrapper.findAll('.rounded').at(0);
        expect(firstRow.findAll('div').at(1).attributes('style')).toContain('width: 100%');
        expect(wrapper.text()).toContain('label:Book');
        expect(wrapper.findAll('.rounded').at(0).attributes('style')).toContain('outline');

        await wrapper.findAll('.rounded').at(1).trigger('click');
        expect(wrapper.emitted('toggle')).toEqual([['Magazine']]);
    });

    it('handles an empty breakdown without producing an invalid maximum', () => {
        const wrapper = mount(BreakdownPanel, { props: { title: 'Empty', rows: [] } });
        expect(wrapper.vm.max).toBe(1);
        expect(wrapper.text()).toContain('—');
    });
});

describe('PubYearPanel', () => {
    it('builds a continuous histogram, colors age bands and applies a range', async () => {
        const wrapper = mount(PubYearPanel, {
            props: {
                items: [
                    { publication_year: currentYear - 12 },
                    { publication_year: currentYear - 12 },
                    { publication_year: currentYear - 7 },
                    { publication_year: currentYear - 2 },
                    { publication_year: null }
                ]
            }
        });

        expect(wrapper.vm.histogram).toHaveLength(11);
        expect(wrapper.vm.histogram[0]).toEqual({ bin: currentYear - 12, count: 2 });
        expect(wrapper.vm.histogram[1]).toEqual({ bin: currentYear - 11, count: 0 });
        expect(wrapper.vm.dataRange).toEqual({ min: currentYear - 12, max: currentYear - 2 });
        expect(wrapper.vm.maxCount).toBe(2);
        expect(wrapper.vm.barColor(currentYear - 12)).toBe('#F24D66');
        expect(wrapper.vm.barColor(currentYear - 7)).toBe('#F2BF33');
        expect(wrapper.vm.barColor(currentYear - 2)).toBe('#4D99F2');

        wrapper.vm.sliderMin = currentYear - 8;
        wrapper.vm.sliderMax = currentYear - 2;
        wrapper.vm.applyRange();
        expect(wrapper.emitted('update:modelMin')).toEqual([[currentYear - 8]]);
        expect(wrapper.emitted('update:modelMax')).toEqual([[currentYear - 2]]);

        expect(wrapper.vm.isInRange(currentYear - 12)).toBe(true);
        await wrapper.setProps({ modelMin: currentYear - 8, modelMax: currentYear - 2 });
        expect(wrapper.vm.isInRange(currentYear - 12)).toBe(false);
        expect(wrapper.vm.isInRange(currentYear - 7)).toBe(true);
    });

    it('returns an empty histogram and clamps crossed handles', () => {
        const wrapper = mount(PubYearPanel, { props: { items: [] } });
        expect(wrapper.vm.histogram).toEqual([]);
        expect(wrapper.vm.dataRange).toEqual({ min: currentYear - 10, max: currentYear });

        wrapper.vm.sliderMin = 2020;
        wrapper.vm.sliderMax = 2020;
        wrapper.vm.clampMin();
        expect(wrapper.vm.sliderMin).toBe(2019);
        wrapper.vm.sliderMin = 2020;
        wrapper.vm.sliderMax = 2020;
        wrapper.vm.clampMax();
        expect(wrapper.vm.sliderMax).toBe(2021);
    });
});

describe('TauxRotationPanel', () => {
    it('bins decimal rotations, uses threshold colors and emits selected bounds', () => {
        const wrapper = mount(TauxRotationPanel, {
            props: {
                items: [
                    { taux_rotation: 1.8 },
                    { taux_rotation: 4 },
                    { taux_rotation: 8.9 },
                    { taux_rotation: null }
                ],
                title: 'Rotation'
            }
        });

        expect(wrapper.vm.panelTitle).toBe('Rotation');
        expect(wrapper.vm.histogram[0]).toEqual({ bin: 0, count: 1 });
        expect(wrapper.vm.histogram[1]).toEqual({ bin: 1, count: 1 });
        expect(wrapper.vm.histogram[4]).toEqual({ bin: 4, count: 1 });
        expect(wrapper.vm.histogram[8]).toEqual({ bin: 8, count: 1 });
        expect(wrapper.vm.dataRange).toEqual({ min: 0, max: 8 });
        expect(wrapper.vm.barColor(3)).toBe('#4D99F2');
        expect(wrapper.vm.barColor(4)).toBe('#F2BF33');
        expect(wrapper.vm.barColor(8)).toBe('#F24D66');

        wrapper.vm.sliderMin = 2;
        wrapper.vm.sliderMax = 6;
        wrapper.vm.applyRange();
        expect(wrapper.emitted('update:modelMin')).toEqual([[2]]);
        expect(wrapper.emitted('update:modelMax')).toEqual([[6]]);
        expect(wrapper.vm.isInRange(1)).toBe(true);
    });

    it('supports a rotation minimum or maximum without inventing the other bound', () => {
        const wrapper = mount(TauxRotationPanel, {
            props: { items: [{ taux_rotation: 1 }, { taux_rotation: 4 }, { taux_rotation: 8 }] }
        });
        wrapper.vm.sliderMin = 2;
        wrapper.vm.sliderMax = wrapper.vm.dataRange.max;
        wrapper.vm.applyRange();
        expect(wrapper.emitted('update:modelMin').at(-1)).toEqual([2]);
        expect(wrapper.emitted('update:modelMax').at(-1)).toEqual([null]);

        wrapper.vm.sliderMin = wrapper.vm.dataRange.min;
        wrapper.vm.sliderMax = 6;
        wrapper.vm.applyRange();
        expect(wrapper.emitted('update:modelMin').at(-1)).toEqual([null]);
        expect(wrapper.emitted('update:modelMax').at(-1)).toEqual([6]);
    });

    it('uses the default range for empty data and clears a default selection', () => {
        const wrapper = mount(TauxRotationPanel, { props: { items: [] } });
        expect(wrapper.vm.histogram).toEqual([]);
        expect(wrapper.vm.dataRange).toEqual({ min: 0, max: 8 });
        wrapper.vm.applyRange();
        expect(wrapper.emitted('update:modelMin')).toEqual([[null]]);
        expect(wrapper.emitted('update:modelMax')).toEqual([[null]]);
    });
});
