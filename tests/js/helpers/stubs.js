/**
 * Minimal component doubles shared by parent-component tests.
 *
 * These stubs expose only the contract needed by the parent. If a child
 * interaction becomes the behavior under test, mount the real child instead.
 */
export const AutocompleteInputStub = {
    template: '<input />',
    setup(_, { expose }) {
        expose({ focusInput: () => {} });
        return {};
    }
};

export const DataTableStub = {
    props: ['columns', 'rows', 'loading', 'emptyMessage'],
    template: '<div><slot name="row" v-for="row in rows" :row="row" /></div>'
};
