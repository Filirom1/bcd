import { afterEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, shallowMount } from '@vue/test-utils';

import { apiClient } from '../../../src/bcd_web_vue/js/api/client.js';
import ActivityTimelinePage from '../../../src/bcd_web_vue/js/pages/ActivityTimelinePage.js';

const mountedWrappers = [];

const action = (id, actionType, occurredAt, title) => ({
    id,
    transaction_id: Number(id.split(':')[0]),
    action: actionType,
    occurred_at: occurredAt,
    borrower_id: 'S-101',
    borrower_name: 'Amira BENALI',
    class_id: 1,
    class_name: 'CP-A',
    homeroom_teacher: 'Mme Dupont',
    item_id: `I-${id}`,
    title
});

function mountPage() {
    const wrapper = shallowMount(ActivityTimelinePage, {
        global: { stubs: { DataTable: false } }
    });
    mountedWrappers.push(wrapper);
    return wrapper;
}

function mockTimelineApi(actionResponses = [[]], activityDays = []) {
    const queuedActions = [...actionResponses];
    return vi.spyOn(apiClient, 'get').mockImplementation(path => {
        if (path === '/circulation/activity-days') return Promise.resolve(activityDays);
        return Promise.resolve(queuedActions.shift() || []);
    });
}

afterEach(() => {
    mountedWrappers.splice(0).forEach(wrapper => wrapper.unmount());
    vi.restoreAllMocks();
});

describe('ActivityTimelinePage', () => {
    it('shows the latest group details by default and requests an actual time range', async () => {
        mockTimelineApi([[
            action('1:return', 'return', '2026-10-19T09:00:00', 'Livre rendu'),
            action('2:checkout', 'checkout', '2026-10-19T09:20:00', 'Livre emprunté'),
            action('3:return', 'return', '2026-10-19T09:45:00', 'Dernier retour')
        ]]);

        const wrapper = mountPage();
        await flushPromises();

        expect(apiClient.get).toHaveBeenCalledWith(
            '/circulation/actions',
            expect.objectContaining({ start: expect.any(String), end: expect.any(String) }),
            { skipGlobalLoading: true }
        );
        expect(wrapper.vm.selectedGroup.id).toBe('3:return');
        expect(wrapper.vm.selectedGroup.students[0].returns[0].title).toBe('Dernier retour');
        expect(wrapper.find('.activity-details-card').exists()).toBe(true);
        expect(wrapper.html().indexOf('activity-details-card'))
            .toBeLessThan(wrapper.html().indexOf('activity-timeline-card'));
    });

    it('moves the default detail to a newly recorded latest group on refresh', async () => {
        const get = mockTimelineApi([
            [
                action('1:return', 'return', '2026-10-19T09:00:00', 'Retour')
            ],
            [
                action('1:return', 'return', '2026-10-19T09:00:00', 'Retour'),
                action('2:checkout', 'checkout', '2026-10-19T09:20:00', 'Emprunt'),
                action('3:return', 'return', '2026-10-19T09:45:00', 'Nouveau groupe')
            ]
        ]);

        const wrapper = mountPage();
        await flushPromises();
        expect(wrapper.vm.selectedGroup.id).toBe('1:return');

        await wrapper.vm.loadActions();
        await flushPromises();

        expect(get.mock.calls.filter(([path]) => path === '/circulation/actions')).toHaveLength(2);
        expect(wrapper.vm.selectedGroup.id).toBe('3:return');
    });

    it('zooms the real time window while keeping its center fixed', async () => {
        mockTimelineApi();
        const wrapper = mountPage();
        await flushPromises();
        await wrapper.vm.shiftWindow(-1);
        await flushPromises();
        const initialCenter = wrapper.vm.rangeStart.getTime() + 2 * 60 * 60 * 1000;

        await wrapper.vm.zoom(-1);
        await flushPromises();

        expect(wrapper.vm.durationHours).toBe(2);
        expect(wrapper.vm.rangeStart.getTime() + 60 * 60 * 1000).toBe(initialCenter);
    });

    it('fits the timeline to a selected day’s activity span', async () => {
        const get = mockTimelineApi([[]], [
            {
                activity_date: '2026-06-26',
                checkout_count: 156,
                return_count: 161,
                first_action_at: '2026-06-26T09:00:00',
                last_action_at: '2026-06-26T11:00:00'
            }
        ]);
        const wrapper = mountPage();
        await flushPromises();

        await wrapper.find('#activity-day-select').setValue('2026-06-26');
        await flushPromises();

        expect(wrapper.vm.durationHours).toBe(4);
        expect(get).toHaveBeenCalledWith(
            '/circulation/actions',
            expect.objectContaining({
                start: '2026-06-26T08:00:00',
                end: '2026-06-26T12:00:00'
            }),
            { skipGlobalLoading: true }
        );
    });

    it('combines simultaneous actions into a thicker colored line', async () => {
        mockTimelineApi([[
            action('1:checkout', 'checkout', '2026-10-19T09:00:00', 'Livre 1'),
            action('2:checkout', 'checkout', '2026-10-19T09:00:00', 'Livre 2')
        ]]);

        const wrapper = mountPage();
        await flushPromises();

        expect(wrapper.vm.timelineEvents).toHaveLength(1);
        expect(wrapper.vm.timelineEvents[0].actionCount).toBe(2);
        expect(wrapper.vm.timelineEvents[0].strokeWidth).toBe(5);
        expect(wrapper.findAll('.activity-timeline-event line')).toHaveLength(1);
    });

    it('shows each student’s returned and borrowed books in separate table columns', async () => {
        mockTimelineApi([[
            action('1:return', 'return', '2026-10-19T09:00:00', 'Livre rendu'),
            action('2:checkout', 'checkout', '2026-10-19T09:10:00', 'Livre emprunté')
        ]]);

        const wrapper = mountPage();
        await flushPromises();

        const row = wrapper.find('.activity-student-table tbody tr');
        const cells = row.findAll('td');
        expect(row.text()).toContain('Amira BENALI');
        expect(cells[0].text()).toContain('Livre rendu');
        expect(cells[1].text()).toContain('Livre emprunté');
    });
});
