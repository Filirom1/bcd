export function makeClass(overrides = {}) {
    return {
        id: 1,
        name: 'CM1',
        homeroom_teacher: 'Mme Martin',
        notes: '',
        average_age: 9,
        ...overrides
    };
}
