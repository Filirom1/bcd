import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { mount } from '@vue/test-utils';

import ConfirmDialog from '../../../../src/bcd_web_vue/js/components/admin/ConfirmDialog.js';
import ProgressIndicator from '../../../../src/bcd_web_vue/js/components/admin/ProgressIndicator.js';
import Modal from '../../../../src/bcd_web_vue/js/components/ui/Modal.js';
import Toast from '../../../../src/bcd_web_vue/js/components/ui/Toast.js';
import NotificationContainer from '../../../../src/bcd_web_vue/js/components/ui/NotificationContainer.js';
import FilterSelect from '../../../../src/bcd_web_vue/js/components/ui/FilterSelect.js';
import NavLink from '../../../../src/bcd_web_vue/js/components/layout/NavLink.js';
import NavigationMenu from '../../../../src/bcd_web_vue/js/components/layout/NavigationMenu.js';
import SidebarNav from '../../../../src/bcd_web_vue/js/components/layout/SidebarNav.js';
import { useNotification } from '../../../../src/bcd_web_vue/js/composables/useNotification.js';
import { useAppState } from '../../../../src/bcd_web_vue/js/composables/useAppState.js';
import { apiClient } from '../../../../src/bcd_web_vue/js/api/client.js';

beforeEach(() => {
    useNotification().clear();
    globalThis.__testRoute.path = '/reports/active-loans';
});

afterEach(() => {
    vi.restoreAllMocks();
    vi.useRealTimers();
    useNotification().clear();
    document.body.innerHTML = '';
});

describe('ConfirmDialog', () => {
    it('limits the displayed item list and emits confirmation actions', async () => {
        const items = Array.from({ length: 12 }, (_, index) => ({ title: `Book ${index}` }));
        const wrapper = mount(ConfirmDialog, {
            props: { show: true, title: 'Confirm', message: 'Delete?', items, count: 12 },
            global: { stubs: { Modal: { template: '<div><slot name="header"/><slot/><slot name="footer"/></div>' } } }
        });
        expect(wrapper.vm.visibleItems).toHaveLength(10);
        expect(wrapper.vm.hiddenCount).toBe(2);
        expect(wrapper.vm.hasMore).toBe(true);
        expect(wrapper.vm.getItemName({ name: 'Name' })).toBe('Name');
        expect(wrapper.vm.getItemName({ full_name: 'Full' })).toBe('Full');
        expect(wrapper.vm.getItemName('raw')).toBe('raw');
        expect(wrapper.text()).toContain('Book 0');
        expect(wrapper.text()).toContain('admin.and_n_more');
        await wrapper.findAll('button').at(0).trigger('click');
        await wrapper.findAll('button').at(1).trigger('click');
        expect(wrapper.emitted('cancel')).toHaveLength(1);
        expect(wrapper.emitted('confirm')).toHaveLength(1);
    });
});

describe('ProgressIndicator', () => {
    it('renders spinner and progress bar variants with estimates', () => {
        const spinner = mount(ProgressIndicator, { props: { operation: 'Loading' } });
        expect(spinner.find('.spinner-border').exists()).toBe(true);
        expect(spinner.vm.progressText).toBe('0%');
        expect(spinner.vm.estimatedTime).toBe(null);

        const bar = mount(ProgressIndicator, {
            props: { showPercentage: true, progress: 40, total: 200, processed: 100, operation: 'Import', variant: 'success' }
        });
        expect(bar.vm.progressBarClass).toBe('progress-bar bg-success');
        expect(bar.vm.progressText).toBe('100 / 200');
        expect(bar.vm.estimatedTime).toBe('~5s remaining');
        expect(bar.find('[role="progressbar"]').attributes('style')).toContain('width: 40%');
        expect(bar.find('.progress-bar').classes()).toContain('bg-success');

        const minutes = mount(ProgressIndicator, { props: { showPercentage: true, total: 2000, processed: 1, progress: 1 } });
        expect(minutes.vm.estimatedTime).toBe('~2m remaining');
    });
});

describe('Modal', () => {
    it('closes from the button, backdrop and Escape unless static', async () => {
        const wrapper = mount(Modal, {
            props: { show: true, title: 'Dialog', size: 'lg', centered: true, scrollable: true },
            slots: { default: 'Body', footer: 'Footer' }
        });
        expect(document.body.querySelector('.modal-lg.modal-dialog-centered.modal-dialog-scrollable')).not.toBeNull();
        document.body.querySelector('.btn-close').click();
        expect(wrapper.emitted('close')).toHaveLength(1);
        wrapper.vm.onBackdropClick();
        expect(wrapper.emitted('close')).toHaveLength(2);
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
        expect(wrapper.emitted('close')).toHaveLength(3);
        wrapper.unmount();

        const staticWrapper = mount(Modal, { props: { show: true, static: true } });
        staticWrapper.vm.onBackdropClick();
        document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
        expect(staticWrapper.emitted('close')).toBeUndefined();
    });
});

describe('Toast and NotificationContainer', () => {
    it('maps notification types, dismisses manually and automatically', async () => {
        vi.useFakeTimers();
        const notification = { id: 7, type: 'success', message: 'Done', duration: 1000 };
        const wrapper = mount(Toast, { props: { notification } });
        expect(wrapper.vm.getTypeClass()).toBe('bg-success');
        expect(wrapper.vm.getIcon()).toBe('bi-check-circle-fill');
        await wrapper.find('button').trigger('click');
        expect(useNotification().notifications.value).toEqual([]);
        vi.advanceTimersByTime(1000);

        const unknown = mount(Toast, { props: { notification: { id: 8, type: 'other', title: 'Alert', duration: 0 } } });
        expect(unknown.vm.getTypeClass()).toBe('bg-secondary');
        expect(unknown.vm.getIcon()).toBe('bi-bell-fill');
        const container = mount(NotificationContainer);
        useNotification().success('Saved', 0);
        await container.vm.$nextTick();
        expect(container.findAll('.toast')).toHaveLength(1);
    });
});

describe('FilterSelect', () => {
    it('supports placeholder visibility and v-model updates', async () => {
        const wrapper = mount(FilterSelect, {
            props: { label: 'Type', modelValue: '', options: [{ value: 'book', label: 'Book' }], placeholder: 'All' }
        });
        expect(wrapper.findAll('option')).toHaveLength(2);
        await wrapper.find('select').setValue('book');
        expect(wrapper.emitted('update:modelValue')).toEqual([['book']]);
        const noPlaceholder = mount(FilterSelect, {
            props: { options: [], showPlaceholder: false }
        });
        expect(noPlaceholder.findAll('option')).toHaveLength(0);
    });
});

describe('Navigation components', () => {
    const routerLink = {
        props: ['to'],
        template: '<a :href="typeof to === \'string\' ? to : \'#\'"><slot :navigate="() => {}" :href="typeof to === \'string\' ? to : \'#\'" :is-active="false" /></a>'
    };

    it('expands active submenus and navigates simple links', async () => {
        const wrapper = mount(NavLink, {
            props: {
                to: '/reports', icon: 'bi-book', label: 'Reports', shortcut: 'R', showShortcut: true,
                submenu: [{ to: '/reports/active-loans', label: 'Active' }]
            },
            global: { stubs: { RouterLink: routerLink } }
        });
        expect(wrapper.vm.isActive).toBe(true);
        expect(wrapper.vm.isExpanded).toBe(true);
        await wrapper.find('a.nav-link').trigger('click');
        expect(wrapper.vm.isExpanded).toBe(false);
        wrapper.vm.toggleSubmenu({ preventDefault: vi.fn() });
        expect(wrapper.vm.isExpanded).toBe(true);

        const simple = mount(NavLink, { props: { to: '/catalog', label: 'Catalog', shortcut: 'C', showShortcut: true }, global: { stubs: { RouterLink: routerLink } } });
        expect(simple.find('kbd').text()).toBe('C');
    });

    it('builds the complete navigation and sidebar health footer', async () => {
        const navItems = mount(NavigationMenu, { global: { stubs: { NavLink: true } } }).vm.navItems;
        expect(navItems).toHaveLength(10);
        expect(navItems.find(item => item.to === '/cataloging')).toBeTruthy();
        expect(navItems.find(item => item.to === '/settings').submenu).toHaveLength(7);
        vi.spyOn(apiClient, 'get').mockResolvedValue({ version: '2.0.0' });
        useAppState().saveSettings({ library_code: 'BCD' });
        const wrapper = mount(SidebarNav, { global: { stubs: { NavigationMenu: true, LanguageSwitcher: true } } });
        await wrapper.vm.$nextTick();
        await new Promise(resolve => setTimeout(resolve, 0));
        expect(wrapper.vm.brandName).toBe('BCD');
        expect(wrapper.vm.appVersion).toBe('2.0.0');
    });
});
