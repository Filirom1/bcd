import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { mount } from '@vue/test-utils';

import BibliographicForm from '../../../../src/bcd_web_vue/js/components/cataloging/BibliographicForm.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';
import { useNotification } from '../../../../src/bcd_web_vue/js/composables/useNotification.js';

const mountedWrappers = [];

function mountForm(props = {}) {
    const wrapper = mount(BibliographicForm, {
        props,
        global: {
            stubs: {
                BibliographicFields: true
            },
            mocks: { $t: key => key }
        }
    });
    mountedWrappers.push(wrapper);
    return wrapper;
}

beforeEach(() => {
    useNotification().clear();
});

afterEach(() => {
    mountedWrappers.splice(0).forEach(wrapper => wrapper.unmount());
    useNotification().clear();
    vi.restoreAllMocks();
});

describe('BibliographicForm', () => {
    it('rejects a blank title before calling the API', async () => {
        const post = vi.spyOn(apiClient, 'post');
        const wrapper = mountForm({ isbn: '978-2-07-061275-8' });

        wrapper.vm.formData.title = '   ';
        await wrapper.vm.submitRecord();

        expect(post).not.toHaveBeenCalled();
        expect(wrapper.emitted('record-created')).toBeUndefined();
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'error', message: 'cataloging.error_title_required' })
        ]);
    });

    it('builds the complete create payload and emits the created record', async () => {
        const created = { id: 42, title: 'Le Petit Prince' };
        const post = vi.spyOn(apiClient, 'post').mockResolvedValue(created);
        const wrapper = mountForm({ isbn: 'isbn:9782070612758' });

        Object.assign(wrapper.vm.formData, {
            title: 'Le Petit Prince',
            subtitle: 'Édition scolaire',
            authors: ['Antoine de Saint-Exupéry'],
            illustrators: ['Antoine de Saint-Exupéry'],
            publisher: 'Gallimard',
            publication_year: 1943,
            collection: 'Folio junior',
            series_number: '12',
            language: 'fr',
            country_code: 'FR',
            binding_type: 'paperback',
            level: 'CM2',
            medium_type: 'Livre',
            target_audience: 'child',
            keywords: ['aventure', 'amitié'],
            description: 'Un aviateur rencontre un enfant venu d’une autre planète.',
            dewey_number: '843',
            page_count: 96,
            has_illustrations: true,
            dimensions: '18 x 11 cm',
            physical_size: '96 pages',
            cover_image: '9782070612758.jpg'
        });

        await wrapper.vm.submitRecord();

        expect(post).toHaveBeenCalledWith('/catalog/bibliographic', {
            isbn: '9782070612758',
            title: 'Le Petit Prince',
            subtitle: 'Édition scolaire',
            authors: ['Antoine de Saint-Exupéry'],
            illustrators: ['Antoine de Saint-Exupéry'],
            publisher: 'Gallimard',
            publication_year: 1943,
            collection: 'Folio junior',
            series_number: '12',
            language: 'fr',
            country_code: 'FR',
            binding_type: 'paperback',
            level: 'CM2',
            medium_type: 'Livre',
            target_audience: 'child',
            keywords: ['aventure', 'amitié'],
            description: 'Un aviateur rencontre un enfant venu d’une autre planète.',
            dewey_number: '843',
            page_count: 96,
            has_illustrations: true,
            dimensions: '18 x 11 cm',
            physical_size: '96 pages',
            cover_image: '9782070612758.jpg'
        });
        expect(wrapper.emitted('record-created')).toEqual([[created]]);
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'success', message: 'cataloging.record_created' })
        ]);
    });

    it('prefills an existing record and sends a PATCH update payload', async () => {
        const existing = {
            id: 7,
            isbn: 'isbn:9782070612758',
            title: 'Ancien titre',
            authors: ['Auteur'],
            illustrators: [],
            language: 'fr',
            country_code: 'FR',
            binding_type: 'hardcover',
            medium_type: 'Livre',
            target_audience: 'child',
            dewey_number: '800',
            page_count: '',
            has_illustrations: false,
            physical_size: '96 pages',
            cover_image: 'old-cover.jpg'
        };
        const updated = { ...existing, title: 'Nouveau titre' };
        const patch = vi.spyOn(apiClient, 'patch').mockResolvedValue(updated);
        const wrapper = mountForm({ existingRecord: existing });

        expect(wrapper.vm.formData).toMatchObject({
            isbn: '9782070612758',
            title: 'Ancien titre',
            country_code: 'FR',
            binding_type: 'hardcover',
            dewey_number: '800',
            has_illustrations: false,
            physical_size: '96 pages',
            cover_image: 'old-cover.jpg'
        });

        wrapper.vm.formData.title = 'Nouveau titre';
        wrapper.vm.formData.page_count = '';
        await wrapper.vm.submitRecord();

        expect(patch).toHaveBeenCalledWith('/catalog/records/7', expect.objectContaining({
            isbn: '9782070612758',
            title: 'Nouveau titre',
            page_count: null,
            publication_year: null,
            country_code: 'FR',
            binding_type: 'hardcover',
            dewey_number: '800'
        }));
        expect(wrapper.emitted('record-created')).toEqual([[updated]]);
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'success', message: 'cataloging.record_updated' })
        ]);
    });

    it('reports API validation failures without emitting a record', async () => {
        vi.spyOn(apiClient, 'post').mockRejectedValue(new Error('invalid title'));
        const wrapper = mountForm();
        wrapper.vm.formData.title = 'Titre valide';

        await wrapper.vm.submitRecord();

        expect(wrapper.emitted('record-created')).toBeUndefined();
        expect(wrapper.vm.loading).toBe(false);
        expect(useNotification().notifications.value).toEqual([
            expect.objectContaining({ type: 'error', message: 'errors.unknown_error' })
        ]);
    });

    it('prefills BNF data, chooses the cover source, and emits cancellation', () => {
        const wrapper = mountForm({
            isbn: '978-000-000-0000',
            bnfData: {
                _source: 'google_books',
                isbn: 'isbn:978-207-061275-8',
                title: 'Le Petit Prince',
                authors: ['Antoine de Saint-Exupéry'],
                cover_url: 'https://books.example/cover.jpg',
                publication_year: 1943,
                has_illustrations: true
            }
        });

        expect(wrapper.vm.isBnfData).toBe(true);
        expect(wrapper.vm.lookupSource).toBe('google_books');
        expect(wrapper.vm.formData).toMatchObject({
            isbn: '9782070612758',
            title: 'Le Petit Prince',
            authors: ['Antoine de Saint-Exupéry'],
            publication_year: 1943,
            has_illustrations: true
        });
        expect(wrapper.vm.coverPreviewUrl).toBe('https://books.example/cover.jpg');

        const localCoverWrapper = mountForm({
            isbn: '978-207-061275-8',
            bnfData: { isbn: '9782070612758', cover_image: 'cover.jpg' }
        });
        const image = { src: 'http://localhost/covers/cover.jpg', style: {} };
        localCoverWrapper.vm.handleCoverError({ target: image });
        expect(image.src).toContain('covers.openlibrary.org/b/isbn/9782070612758');

        wrapper.vm.cancel();
        expect(wrapper.emitted('cancel')).toHaveLength(1);
    });
});
