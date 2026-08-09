export function makeBorrower(overrides = {}) {
    return {
        id: 1,
        borrower_id: 'B-101',
        first_name: 'Amira',
        last_name: 'Benali',
        full_name: 'Amira Benali',
        active: true,
        current_loans_count: 0,
        loan_limit: 3,
        status: 'active',
        ...overrides
    };
}
