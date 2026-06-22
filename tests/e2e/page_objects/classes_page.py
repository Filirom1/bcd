"""
Classes Page Object

Handles class management operations (CRUD).
"""

from playwright.sync_api import Page

from tests.e2e.page_objects.base_page import BasePage


class ClassesPage(BasePage):
    """Page object for class management."""

    # Selectors
    CREATE_CLASS_BUTTON = 'button:has-text("Create Class"), button:has-text("Créer une classe")'
    CLASS_TABLE = 'table tbody tr'
    CLASS_NAME_INPUT = 'input[name="name"], input#className'
    HOMEROOM_TEACHER_INPUT = 'input[name="homeroom_teacher"], input#homeroomTeacher'
    NOTES_TEXTAREA = 'textarea[name="notes"], textarea#notes'
    SAVE_BUTTON = 'button:has-text("Save"), button:has-text("Enregistrer"), button.btn-primary:has-text("Save"), button.btn-primary:has-text("Enregistrer")'
    CANCEL_BUTTON = 'button:has-text("Cancel"), button:has-text("Annuler")'
    EDIT_BUTTON = 'button:has-text("Edit"), button:has-text("Modifier"), a:has-text("Edit"), a:has-text("Modifier")'
    DELETE_BUTTON = 'button:has-text("Delete"), button:has-text("Supprimer")'
    CONFIRM_DELETE_BUTTON = 'button.btn-danger:has-text("Delete"), button.btn-danger:has-text("Supprimer")'
    MODAL = '.modal.show'
    FORM_MODAL = '#classFormModal'
    DELETE_MODAL = '#classDeleteDialog'

    def __init__(self, page: Page, server_url: str):
        super().__init__(page, server_url)

    def goto(self):
        """Navigate to classes page."""
        self.navigate_to('classes')
        self.wait_for_table_load()

    def wait_for_table_load(self, timeout=10000):
        """Wait for classes table to load."""
        # Wait for either table or empty state
        try:
            self.wait_for_selector(self.CLASS_TABLE, timeout=timeout)
        except:
            # Table might be empty - check for "no data" message
            pass

    def click_create_class(self):
        """Click Create Class button."""
        self.click(self.CREATE_CLASS_BUTTON)
        self.wait_for_modal()

    def wait_for_modal(self, timeout=5000):
        """Wait for modal to open."""
        self.wait_for_selector(self.MODAL, timeout=timeout)

    def fill_class_form(self, name: str, homeroom_teacher: str = None, notes: str = None):
        """
        Fill class form with data.

        Args:
            name: Class name (required)
            homeroom_teacher: Homeroom teacher name (optional)
            notes: Additional notes (optional)
        """
        # Wait for modal to be fully loaded
        self.page.wait_for_timeout(500)

        # Fill name (required)
        name_input = self.page.locator(self.CLASS_NAME_INPUT).first
        name_input.fill(name)

        # Fill homeroom teacher (optional)
        if homeroom_teacher:
            teacher_input = self.page.locator(self.HOMEROOM_TEACHER_INPUT).first
            if teacher_input.count() > 0:
                teacher_input.fill(homeroom_teacher)

        # Fill notes (optional)
        if notes:
            notes_textarea = self.page.locator(self.NOTES_TEXTAREA).first
            if notes_textarea.count() > 0:
                notes_textarea.fill(notes)

    def save_form(self):
        """Click Save button in form modal."""
        # Find Save button within the modal
        modal = self.page.locator(self.MODAL).first
        save_button = modal.locator(self.SAVE_BUTTON).first
        save_button.click()
        self.page.wait_for_timeout(1000)

    def create_class(self, name: str, homeroom_teacher: str = None, notes: str = None):
        """
        Create a new class.

        Args:
            name: Class name
            homeroom_teacher: Homeroom teacher name (optional)
            notes: Additional notes (optional)
        """
        self.click_create_class()
        self.fill_class_form(name, homeroom_teacher, notes)
        self.save_form()

    def get_class_count(self) -> int:
        """Get number of classes in table."""
        return self.page.locator(self.CLASS_TABLE).count()

    def get_class_row_by_name(self, class_name: str):
        """Get table row for a specific class by name."""
        # Find row containing the class name
        return self.page.locator(f'tr:has-text("{class_name}")').first

    def click_edit_class(self, class_name: str):
        """
        Click edit button for a specific class.

        Args:
            class_name: Name of class to edit
        """
        row = self.get_class_row_by_name(class_name)
        edit_button = row.locator(self.EDIT_BUTTON).first
        edit_button.click()
        self.wait_for_modal()

    def edit_class(self, class_name: str, new_name: str = None, new_teacher: str = None, new_notes: str = None):
        """
        Edit an existing class.

        Args:
            class_name: Current name of class to edit
            new_name: New class name (if changing)
            new_teacher: New homeroom teacher (if changing)
            new_notes: New notes (if changing)
        """
        self.click_edit_class(class_name)

        if new_name:
            name_input = self.page.locator(self.CLASS_NAME_INPUT).first
            name_input.fill('')  # Clear first
            name_input.fill(new_name)

        if new_teacher:
            teacher_input = self.page.locator(self.HOMEROOM_TEACHER_INPUT).first
            if teacher_input.count() > 0:
                teacher_input.fill('')
                teacher_input.fill(new_teacher)

        if new_notes:
            notes_textarea = self.page.locator(self.NOTES_TEXTAREA).first
            if notes_textarea.count() > 0:
                notes_textarea.fill('')
                notes_textarea.fill(new_notes)

        self.save_form()

    def click_delete_class(self, class_name: str):
        """
        Click delete button for a specific class.

        Args:
            class_name: Name of class to delete
        """
        row = self.get_class_row_by_name(class_name)
        delete_button = row.locator(self.DELETE_BUTTON).first
        delete_button.click()
        self.page.wait_for_timeout(500)

    def confirm_delete(self):
        """Confirm deletion in delete confirmation modal."""
        # Wait for delete confirmation modal
        self.page.wait_for_timeout(500)
        confirm_button = self.page.locator(self.CONFIRM_DELETE_BUTTON).first
        confirm_button.click()
        self.page.wait_for_timeout(1000)

    def delete_class(self, class_name: str):
        """
        Delete a class with confirmation.

        Args:
            class_name: Name of class to delete
        """
        self.click_delete_class(class_name)
        self.confirm_delete()

    def get_student_count_for_class(self, class_name: str) -> int:
        """
        Get student count displayed for a class.

        Args:
            class_name: Name of class

        Returns:
            Student count (0 if not found or can't parse)
        """
        row = self.get_class_row_by_name(class_name)
        if row.count() == 0:
            return 0

        # Try to extract student count from row text
        row_text = row.inner_text()
        # Look for number in row (simple approach - may need refinement)
        import re
        numbers = re.findall(r'\d+', row_text)
        if numbers:
            # Assume last number is student count
            return int(numbers[-1])
        return 0

    def class_exists(self, class_name: str) -> bool:
        """Check if a class exists in the table."""
        return self.get_class_row_by_name(class_name).count() > 0
