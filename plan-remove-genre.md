# Migration Plan: Removing the "Genre" Field in Favor of "Shelf Location"

This document provides a comprehensive roadmap for eliminating the redundant **Genre** field from the BCD library system. The classification of books will rely entirely on the physical **Shelf Location** (`shelf_location`) of book items, simplifying the cataloging process, reducing duplicate fields, and enhancing rule-based call number generation.

---

## 1. Architectural Motivation

In the BCD school library system, the **Genre** of a bibliographic record (e.g., "Roman", "Album", "Documentaire") and the physical **Shelf Location** of its items (e.g., "Romans", "Albums", "Documentaires") are 95% redundant.
- **Genre** was stored at the `bibliographic_record` (book) level.
- **Shelf Location** is stored at the `item` (copy/exemplaire) level.

To simplify the user experience and codebase:
1. We will **eliminate** the `genre` field from the database entirely.
2. We will **transfer existing genre data** to the copy-level `shelf_location` field during migration (ensuring no data is lost).
3. The dynamic call number generation rules (used to compute cotes like `R LAF` or `598.9 PAR`) will match against the item's **Shelf Location** rather than the book's **Genre**.
4. In the Kids interface, filters will be simplified to use Shelf Location.

---

## 2. Phase-by-Phase Roadmap

### Phase 1: Database Migration (Alembic)
Create a new Alembic migration script (`alembic revision -m "remove_genre_field"`):
* **`upgrade()` step:**
  1. For every physical `item` where `shelf_location` is empty or null, look up its parent `bibliographic_record`'s `genre`. Copy this genre value (e.g., "Roman" $\rightarrow$ "Romans") to the item's `shelf_location` so no operational information is lost.
  2. Update the `system_settings` table to migrate the JSON array `catalog_call_number_rules`. Change the rule keys from `"genre"` to `"shelf_location"`.
  3. Drop the `genre` column from the `bibliographic_record` table.
* **`downgrade()` step:**
  1. Restore the `genre` column on `bibliographic_record`.
  2. Populate `bibliographic_record.genre` by taking the first available `shelf_location` from its physical items.
  3. Revert `catalog_call_number_rules` to use the `"genre"` property.

### Phase 2: Backend and Schemas Refactoring (FastAPI)
1. **Models (`src/bcd_api/models/`)**:
   - `bibliographic_record.py`: Remove `genre = Column(String(100), ...)` column.
   - `system_settings.py`: Update the default JSON in `catalog_call_number_rules` to use `shelf_location` instead of `genre`:
     ```json
     [
       {"medium_type": "Périodique", "shelf_location": null, "pattern": ""},
       {"medium_type": null, "shelf_location": "Albums", "pattern": "A {AUT1}"},
       {"medium_type": null, "shelf_location": "Romans", "pattern": "R {AUT3}"},
       {"medium_type": null, "shelf_location": "Contes", "pattern": "C {AUT1}"},
       {"medium_type": null, "shelf_location": "Poésie", "pattern": "P {AUT1}"},
       {"medium_type": null, "shelf_location": "Théâtre", "pattern": "T {AUT1}"},
       {"medium_type": null, "shelf_location": "Bandes dessinées", "pattern": "BD {AUT1}"},
       {"medium_type": null, "shelf_location": "Mangas", "pattern": "M {AUT1}"},
       {"medium_type": null, "shelf_location": "Documentaires", "pattern": "{DEWEY} {AUT3}"},
       {"medium_type": null, "shelf_location": null, "pattern": "{AUT3}"}
     ]
     ```
2. **Schemas (`src/bcd_api/schemas/`)**:
   - Remove `genre` from Pydantic schemas: `BibliographicRecordCreate`, `BibliographicRecordUpdate`, `BibliographicRecordResponse` (`bibliographic_record.py`), and `InventoryItem` (`inventory.py`).
3. **Services (`src/bcd_api/services/`)**:
   - `catalog_service.py`: Remove filtering and bulk updates by `genre`.
   - `inventory_service.py`: Remove `genre` query parsing, filtering, and bulk record editing updates.
   - `report_service.py`: Remove the "By genre" breakdowns. Instead, leverage "By shelf location" as the primary breakdown for collection analytics.
   - `import_service.py`: When importing catalog CSVs, if a `Genre` column is present, automatically map it to populate the `shelf_location` field of the physical items created.

### Phase 3: Web UI Simplification (Vue 3)
1. **Cataloging & Edit Forms (`BibliographicForm.js`, `RecordEditForm.js`)**:
   - Remove the `Genre` input field and its datalist of suggestions completely.
2. **Item Barcode Creator (`ItemBarcodeInput.js`)**:
   - Refactor the suggested call number calculation. Instead of computing it based on `recordGenre`, compute it dynamically in response to changes in the selected `shelfLocation` dropdown!
   - This provides immediate reactive cotes (e.g. selecting the "Romans" shelf location automatically suggests `R LAF`).
3. **Advanced Filters & Results (`AdvancedFilters.js`, `SearchResults.js`, `RecordDetail.js`)**:
   - Remove the `genre` filter from advanced search.
   - Remove the `genre` badge/column in search tables and detail modals.
   - Remove the `genre` field from the bulk editing modal.
4. **Reports Dashboard (`CollectionReport.js`, `MostBorrowedReport.js`, `NeverBorrowedReport.js`)**:
   - Delete the "By genre" cards/graphs, ensuring the dashboard looks clean and focuses entirely on physical "Shelf Location".

### Phase 4: Kids Client Updates (Godot)
1. **Filter Panel (`bcd_kids/src/components/FilterPanel.gd` & `.tscn`)**:
   - Remove the "Genre" dropdown option from search filters.
2. **Book Details Screen (`bcd_kids/src/screens/SBookDetail.gd`)**:
   - Remove the "Genre" label and value row from the metadata grid.
3. **API & Localization (`bcd_kids/autoload/API.gd`, `locales/*.json`)**:
   - Remove the `genre` filter parameter append in HTTP requests.
   - Delete `filter_genre` translation strings.

---

## 3. Reference Checklist of Source Code Occurrences

Here is the exact list of files and line numbers where the word `genre` needs to be cleaned up or adapted:

### Database & Models
- **`src/bcd_api/models/system_settings.py`**
  - Line 77: Comment on rule schemas.
  - Line 78: Default JSON for `catalog_call_number_rules`.
- **`src/bcd_api/models/bibliographic_record.py`**
  - Line 43: DB Column definition: `genre = Column(String(100), ...)`

### Schemas & DTOs
- **`src/bcd_api/schemas/bibliographic_record.py`**
  - Lines 32, 90, 133: Pydantic field definition and examples.
- **`src/bcd_api/schemas/inventory.py`**
  - Lines 25, 76, 128, 137, 163: Fields and example payloads.
- **`src/bcd_api/schemas/admin.py`**
  - Lines 74, 76: Bulk update action schemas.

### REST API Endpoints
- **`src/bcd_api/api/v1/catalog.py`**
  - Lines 123, 143, 159, 258: Request Query parameters and response dictionaries.
- **`src/bcd_api/api/v1/inventory.py`**
  - Lines 70, 128, 147, 170, 201: Inventory filters and updates.
- **`src/bcd_api/api/v1/reports.py`**
  - Lines 25, 38, 40, 48, 122, 137, 153, 179, 198: Report endpoints and routing filters.
- **`src/bcd_api/api/v1/admin.py`**
  - Line 579: Admin routes for bulk modifications.

### Backend Services
- **`src/bcd_api/services/settings_service.py`**
  - Line 25: `DEFAULT_CALL_NUMBER_RULES` initial JSON array.
- **`src/bcd_api/services/catalog_service.py`**
  - Lines 308, 329, 390, 391, 615, 633, 653, 654: CRUD operations and filters.
- **`src/bcd_api/services/inventory_service.py`**
  - Lines 140, 165, 186, 290-294, 336, 372, 419: Inventory queries and updates.
- **`src/bcd_api/services/report_service.py`**
  - Lines 37, 49, 57, 112, 113, 148, 189, 317, 330, 368-370, 409, 432, 466, 481, 482, 494, 516: Report generation logic.
- **`src/bcd_api/services/import_service.py`**
  - Line 18: CSV Column Header Mapping.
- **`src/bcd_api/services/dublin_core_import.py`**
  - Line 139: Mapping translation dictionary.

### Web UI (Vue 3 Client)
- **`src/bcd_web_vue/js/composables/`**
  - `useColumnSettings.js:24`: Grid columns configuration.
  - `useReportFilters.js:3, 13, 58, 88`: Client-side report filtering.
  - `useInventoryColumnSettings.js:25`: Inventory column picker.
  - `useBulkOperations.js:159`: Bulk operation parameters.
  - `useInventoryTable.js:95`: Table row mapping.
- **`src/bcd_web_vue/js/components/cataloging/`**
  - `BibliographicForm.js:57, 93, 121, 460-473`: Sizing, form data model, and input HTML.
  - `ItemBarcodeInput.js:99, 100, 104, 124, 131`: Dynamic shelf location and rule calculation.
- **`src/bcd_web_vue/js/components/catalog/`**
  - `RecordEditForm.js:69, 135, 691-707`: Form fields and suggestions.
  - `RecordDetail.js:466-468`: Bibliographic record details modal table.
  - `SearchResults.js:80, 264, 363-369`: Table headers, columns, and badge elements.
  - `AdvancedFilters.js:3, 78, 190-201`: Filters panel layout and listeners.
  - `BulkEditModal.js:50, 121-122, 155, 370-382`: Bulk edit options for catalog.
- **`src/bcd_web_vue/js/components/inventory/`**
  - `BulkEditPanel.js:42, 91, 130, 131, 159, 246-254`: Bulk editing inventory records.
  - `SearchTab.js:49, 127, 195, 381-391`: Search and filter layouts.
  - `InventoryResults.js:67, 296-298`: Column settings and cell renderers.
- **`src/bcd_web_vue/js/components/reports/`**
  - `CollectionReport.js:20, 39, 80, 263, 280, 309, 343, 823-839`: Dashboard cards and panel renderers.
  - `MostBorrowedReport.js:25, 68, 124, 313-320, 391`: Breakdowns and search summaries.
  - `NeverBorrowedReport.js:61, 251-252, 522-534`: Crew score filter dropdowns.
- **`src/bcd_web_vue/js/components/settings/`**
  - `SettingsForm.js:120, 641`: Sizing rules for call number patterns.
- **`src/bcd_web_vue/js/pages/`**
  - `CatalogPage.js:92, 151, 152, 188, 189, 235, 236`: Page query parsing and API sync.
  - `CatalogingPage.js:73, 88, 236`: Prop passing during item creation.
  - `InventoryPage.js:493`: Mapping returned records.
- **`src/bcd_web_vue/locales/`**
  - `en.json:171, 388, 560, 608, 777, 1014, 1109-1110, 1240`: Translation keys.
  - `fr.json:171, 388, 561, 609, 778, 1015, 1110-1111, 1241`: Translation keys.

### Godot Client (Kids App)
- **`bcd_kids/src/screens/SBookDetail.gd:46`**: Metadata grid mapping.
- **`bcd_kids/src/components/FilterPanel.gd:41` & `.tscn:30`**: Search filters layout.
- **`bcd_kids/autoload/API.gd:122-123`**: HTTP query construction.
- **`bcd_kids/locales/en.json:71`**: Translation labels.
- **`bcd_kids/locales/fr.json:71`**: Translation labels.
- **`bcd_kids/README.md` & `README_FR.md`**: References to searching by genre in documentation.
- **`bcd_kids/TECHNICAL.md`**: References to dynamic filter panels.

### Documentation & Markdown Files (.md)
The following markdown files and help docs must be updated to remove references to "genre" and redirect references towards "shelf location" or physical classification:
- **`README.md` & `README_FR.md`** (Project Root): References to "genre" in search filters, metadata reviews, working table bulk edits, and CREW reports.
- **`docs/help/fr/` & `docs/help/en/`**:
  - `settings.md` / `parametres.md`: Configuration tables and advice for genre fields.
  - `catalog.md` / `catalogue.md`: Explanations on literary sub-categories and "unifying genre variants" via bulk edit.
  - `cataloging.md` / `catalogage.md`: Data-entry descriptions of genres.
  - `inventory.md` / `inventaire.md`: Filtering record-level values in inventory mode.
  - `reports.md` / `rapports.md`: Section on "By genre" dashboards and rotation insights.
- **`specs/`** (Functional Specifications):
  - `specs/013-rapports-fonds-agreg/spec.md`: Multi-dimensional collection breakdown specifications based on genre filters and histograms.
  - `specs/008-inventory-page/contracts/api-endpoints.md`: Partial match parameters for inventory search.
  - `specs/006-admin-features/data-model.md`, `spec.md`, `tasks.md`: Specifications, models, and task descriptions for bulk-editing categories and genres.
  - `specs/008-inventory-page/spec.md`, `data-model.md`, `tasks.md`: Specifications, data models, and tasks mapping the inventory's record filters to the genre field.
  - `specs/001-school-library-system/plan.md`, `data-model.md`, `tasks.md`, `quickstart.md`, `research.md`: Historic core design planning linking imports to genres.
  - `specs/005-csv-import/data-model.md`, `research.md`: Analysis of genrefication in schools and schema properties.
  - `specs/012-cote-emplacement/spec.md`, `plan.md`: Mockups and specifications on call numbers and locations.
- **`DENORMALIZATION.md`** (Database patterns): Notes about `system_settings` storing lists like `catalog_genres`.

