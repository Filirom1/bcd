import { afterEach, describe, expect, it, vi } from 'vitest';
import { flushPromises, mount } from '@vue/test-utils';

import BorrowerImport from '../../../../src/bcd_web_vue/js/components/borrowers/BorrowerImport.js';

function mountImport() {
    return mount(BorrowerImport, {
        props: { show: true },
        global: {
            mocks: { $t: key => key },
            stubs: {
                Modal: {
                    template: '<div><slot name="header" /><slot /><slot name="footer" /></div>'
                }
            }
        }
    });
}

afterEach(() => {
    vi.restoreAllMocks();
});

describe('BorrowerImport', () => {
    it('posts a CSV and keeps the API result shape', async () => {
        const fetchMock = vi.fn().mockImplementation((url) => {
            const body = url.includes('/borrowers/importers')
                ? { importers: [{ name: 'bcd', description: 'BCD CSV' }, { name: 'onde', description: 'ONDE CSV' }] }
                : {
                    total_rows: 2,
                    successful_rows: 2,
                    failed_rows: 0,
                    borrowers_created: 2,
                    borrowers_updated: 0,
                    errors: []
                };
            return Promise.resolve(new Response(JSON.stringify(body), {
                status: 200,
                headers: { 'Content-Type': 'application/json' }
            }));
        });
        vi.stubGlobal('fetch', fetchMock);

        const wrapper = mountImport();
        wrapper.vm.selectedFile = new File(
            ['borrower_id,external_id,first_name,last_name,role,class,active\n,INE-1,Marie,Dupont,student,CP A,true'],
            'students.csv',
            { type: 'text/csv' }
        );

        await wrapper.vm.startImport();
        await flushPromises();

        expect(fetchMock).toHaveBeenCalledWith(
            expect.stringContaining('/api/v1/borrowers/import'),
            expect.objectContaining({ method: 'POST' })
        );
        expect(wrapper.vm.importResult.successful_rows).toBe(2);
        expect(wrapper.vm.importResult.borrowers_created).toBe(2);
    });

    it('emits completion for successful_rows returned by the API', async () => {
        const wrapper = mountImport();
        wrapper.vm.importResult = {
            total_rows: 1,
            successful_rows: 1,
            failed_rows: 0,
            borrowers_created: 1,
            borrowers_updated: 0,
            errors: []
        };

        wrapper.vm.onImportComplete();

        expect(wrapper.emitted('import-complete')).toHaveLength(1);
        expect(wrapper.emitted('close')).toHaveLength(1);
    });
});
