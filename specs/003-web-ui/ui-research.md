# UI Research: Library Management Systems
# Interface Design Patterns and Conventions

**Project**: BCD (Bibliothèque Centre Documentaire) Web UI
**Date**: 2026-01-30
**Context**: Building a web UI for a French elementary school library system

## Executive Summary

This research examines UI patterns and design conventions from existing library management systems, both open-source and commercial. The goal is to identify proven UX patterns for librarian workflows, with particular attention to circulation operations, catalog search, borrower management, barcode scanning integration, and bilingual (French/English) implementations.

### Key Findings

1. **Simplicity is paramount** for elementary school libraries - interfaces should minimize clicks and support rapid, repetitive operations
2. **Barcode scanning** is universally implemented as standard keyboard input (HID mode), requiring no special UI considerations
3. **Color-coded status indicators** are standard across systems (green=available, orange/yellow=on loan, red=overdue)
4. **Module-based navigation** with dropdown menus is the dominant pattern for staff interfaces
5. **Responsive design** is now expected, supporting desktop, tablet, and mobile devices
6. **French localization** is well-supported in major open-source systems, particularly Koha

---

## 1. Open-Source Library Systems Analysis

### 1.1 Koha ILS (Integrated Library System)

**Overview**: The world's first free and open-source integrated library system, originally developed in New Zealand. Widely adopted globally with strong international community support.

#### Circulation Workflow UI

**Checkout Interface**:
- **Primary access**: Function key (F1) or menu: Circulation → Check Out
- **Tabbed interface** for different circulation functions
- **Two-step process**:
  1. Enter patron barcode or partial name search
  2. Scan item barcodes sequentially
- **Real-time feedback**: Each scanned item appears in list with confirmation
- **Patron information panel**: Shows current loans, overdue items, checkout count
- **Visual warnings**: Prominent display when patron has overdue items
- **Email checkout receipts**: Optional email delivery with envelope icon indicator

**Check-In Interface**:
- **Dedicated check-in view**: Circulation → Check In
- **Single-step process**: Scan item barcodes directly
- **Immediate feedback**: Confirmation message for each return
- **Exception handling**: Visual alerts for damaged items, holds, overdue status

**Navigation Pattern**:
- **Breadcrumb navigation**: Shows module location and current page
- **Module bar**: Persistent navigation across all screens
- **Search-first approach**: Primary module-specific search highlighted at top
- **Orientation aids**: User always knows where they are in the system

#### Catalog Search Interface

**Search Features**:
- **Auto-complete**: Available in standard interface
- **OWL children's interface**: Special auto-complete for young users
- **Multiple search modes**: Title, author, ISBN, subject
- **Awards field**: Special search capability with auto-completion
- **MARC integration**: Full bibliographic data support

**Results Display**:
- **Relevance ranking**: Default sort by relevance
- **Availability indicators**: Clear status for each copy
- **Detail view**: Full bibliographic information with all copies

#### Borrower Management

**Patron Records**:
- **Comprehensive patron view**: All patron information on single screen
- **Current loans display**: Items currently checked out with due dates
- **Circulation history**: Past transactions
- **Automated messaging**: System sends due date reminders and notifications
- **Patron self-service**: Web-based patron access to view their account

#### Barcode Scanning Integration

**Implementation**:
- **Standard HID keyboard mode**: Scanners emit regular keyboard input
- **No special configuration**: Works like manual typing with Enter key
- **Fallback support**: Manual entry always available

#### French/Bilingual Support

**Localization**:
- **Full French translation**: Interface available in French since 2001
- **Multi-language support**: French, German, Chinese, Spanish, and many others
- **Configurable interface**: Very adaptable and customizable
- **French institutional use**:
  - Widely used in French public libraries
  - Higher education institutions
  - CDI (Centres de Documentation et d'Information) in schools
- **Support providers**: Three companies in France (BibLibre, Tamil, Progilone), Solutions inLibro in Canada

**French School Implementation Example**:
- Catholic school board in Canada uses Koha for multiple école libraries
- Login interface lists numerous school libraries
- Demonstrates successful deployment in French educational context

#### UI Design Principles

**From Koha Interface Patterns Wiki**:
1. **Breadcrumb navigation**: Two functions - orientation and showing current location
2. **Module-specific search**: Primary search highlighted at top of each module
3. **Responsive design**: Works on desktops, laptops, tablets, smartphones
4. **Configurable appearance**: Easy customization for different contexts
5. **Print templates**: Customizable receipt and notice templates

**Sources**:
- [Koha Interface Patterns Wiki](https://wiki.koha-community.org/wiki/Interface_patterns)
- [Koha Features | KohaSupport](https://kohasupport.com/koha/)
- [Koha - Equinox Open Library Initiative](https://www.equinoxoli.org/products/koha/)
- [Installations en France - Association KohaLa](https://koha-fr.org/installations-en-france/)
- [Koha (logiciel) — Wikipédia](https://fr.wikipedia.org/wiki/Koha_(logiciel))

---

### 1.2 Evergreen ILS

**Overview**: Highly scalable library system developed by Georgia Public Library Service. Known for consortium support and robust architecture.

#### UI Design System

**Style Guide Development**:
- **UI Interest Group**: Active community working on design system
- **Component pattern library**: Reusable UI components
- **Written style guide**: Documented design principles
- **Regular meetings**: 4th Thursday of each month

**Core Design Principles**:

1. **User-Centered Design**:
   - Simplicity of tasks
   - White space utilization
   - Intuitive navigation
   - Professional appearance

2. **Progressive Disclosure**:
   - Staged disclosure patterns
   - Avoids cluttered interfaces
   - Reveals complexity gradually

3. **Visual Consistency**:
   - Makes UI easier to use
   - Professional and reliable impression
   - Reduces learning curve

#### Interface Structure

**Module Bar**:
- **Persistent across all screens**
- **Height**: 2.5em
- **Width**: Adapts to screen resolution
- **Margin**: 3em
- **Dropdown menus**: Appear on click
- **Action grouping**: All actions divided and grouped by module

**Tabbed Interface**:
- **Function key access**: F1 for Circulation → Check Out
- **Multiple tabs**: Different circulation functions
- **Context preservation**: Tab state maintained

#### Circulation Features

**Checkout Process**:
- **Tabbed interface**: Clean separation of functions
- **Real-time display**: Items listed as scanned
- **Non-cataloged items**: Special handling for exceptions
- **Confirmation messages**: Clear feedback for each action

**Check-In Process**:
- **Toolbar access**: Circulation and Patrons → Check In Items
- **Direct scanning**: Barcode entry with submit
- **Exception handling**: Visual alerts for special cases

**Email Receipts**:
- **Patron preference**: Opt-in for email receipts
- **Visual indicators**: Envelope icon (opted in) vs printer icon (not opted in)
- **Integration**: Built into checkout screen

#### Self-Checkout

**Patron-Facing Interface**:
1. **Patron scans barcode** (self-identification)
2. **Item scanning**: Sequential barcode scans
3. **Item listing**: Display below with confirmations
4. **Checkout confirmation**: Clear success messages

#### Offline Circulation

**Resilience Features**:
- **Offline mode**: Continues operation without internet
- **Transaction queuing**: Syncs when connection restored
- **Visual differentiation**: Shows online/offline status

**Technical Evolution**:
- **Legacy**: Mozilla XUL
- **Version 3.0**: AngularJS
- **Current**: Transitioning to Angular
- **Responsive design**: All interfaces mobile-friendly

**Sources**:
- [Evergreen UI Style Guide](https://evergreen-ils.org/documentation/previews/proposed_style_guide.html)
- [UI Interest Group - Evergreen DokuWiki](https://wiki.evergreen-ils.org/doku.php?id=community:ui_ig)
- [Circulation Demo Release](https://evergreen-ils.org/circulation-demo-release/)
- [Circulating Items :: Evergreen Documentation](https://docs.evergreen-ils.org/docs/latest/circulation/circulating_items_web_client.html)

---

### 1.3 OPALS (Online Public Access Library System)

**Overview**: Open-source system designed specifically for school libraries, with emphasis on resource sharing and union catalogs.

#### School Library Focus

**Target Users**:
- **School libraries**: Primary market
- **College libraries**: Secondary market
- **Library consortia**: Union catalogs for ILL services
- **District-wide implementations**: Shared resources across schools

**Design Philosophy**:
- **Web-based entirely**: No client software installation
- **Traditional interface**: Familiar catalog design
- **Staff access via web**: Browser-based administration
- **Resource sharing**: High level of cooperation between libraries

#### Catalog Search

**Search Features**:
- **Auto-complete**: Search suggestions
- **OWL children's interface**: Special interface for young users
- **Awards field search**: Subject-specific searching
- **Auto-completion**: Dynamic search assistance

**Technical Approach**:
- **100% web-based**: Both OPAC and staff client
- **No software installation**: Works from any browser
- **Internet access databases**: Cloud-oriented approach

#### User Satisfaction

**2025 Survey Results** (among school libraries):
- **Highest ratings**: Every evaluated category
- **Reliability**: Premier rating
- **Technical support**: Responsive
- **Cost effectiveness**: Exceptional value

**Deployment Scale**:
- **Multiple library types**: School, college, research, business, religious
- **Union catalogs**: Consortium support
- **ILL services**: Resource sharing enabled
- **District implementations**: Scalable across organizations

**Sources**:
- [OPALS](https://opalsinfo.net/)
- [Library Technology Guides: OPALS Profile](https://librarytechnology.org/product/opals/)
- [OPALS - ONC BOCES School Library System](https://oncboces.libguides.com/SLS/OPALS)

---

## 2. Commercial Systems Analysis

### 2.1 Alexandria Library Software

**Overview**: Commercial library automation software with strong presence in school libraries. Known for user-friendly interface and robust features.

#### Patron/Borrower Management

**Librarian Functions**:
- **Create and edit patrons**: Full CRUD operations
- **Fines and fees management**: Integrated billing
- **Proxy actions**: Perform actions on patron behalf
- **Streamlined workflow**: Keeps library running smoothly

**Patron Access Features**:

**Circulation Summary View**:
- **Current checkouts**: Items on loan
- **Fines display**: Outstanding charges
- **Checkout history**: Past transactions
- **Account settings**: Limited self-service

**Self-Service Capabilities**:
- **Material search**: Various criteria (title, author, genre)
- **Due date visibility**: Clear loan information
- **Holds management**: Reserve items
- **Fines and fees view**: Account balance

#### Circulation Interface

**Robust Features**:
- **All transaction types**: Checkout, return, holds, weeding
- **Seamless workflow**: Integrated operations
- **No app downloads**: Browser-based access
- **Any device compatibility**: Desktop, tablet, mobile

**Automation Features**:
- **Updated patron records**: Automatic synchronization
- **Nightly data cleanup**: Scheduled maintenance
- **Configurable automation**: Set it and forget it

#### Search and Discovery

**Patron Search**:
- **Multiple criteria**: Title, author, genre, keyword
- **Easy discovery**: Intuitive interface
- **Quick results**: Fast search execution

**Interface Characteristics**:
- **Powerful automation**: Comprehensive feature set
- **Customizable interface**: Adaptable to needs
- **Empowers users**: Both patrons and librarians

**Platform Access**:
- **Browser-based**: No installation required
- **Multi-device**: Works everywhere
- **Cloud architecture**: Always accessible

**Sources**:
- [Alexandria Library Management Solutions](https://www.goalexandria.com/)
- [Integrated Library System | Alexandria Library Software](https://www.goalexandria.com/home/)
- [Alexandria Library Management](https://www.schooldataleadership.org/systems/library-textbook-management/alexandria-library-management.html)

---

### 2.2 Follett Destiny Library Manager

**Overview**: Major commercial library system widely deployed in K-12 schools. Known for comprehensive features and mobile support.

#### Interface Structure

**Main Navigation Tabs**:
1. **Circulation**: Primary operations
2. **Reports**: Statistics and analytics
3. **Back Office**: Administration and configuration

**Hierarchical Organization**:
- **Tabs**: Top-level navigation
- **Options**: Functions within each tab
- **Subtabs**: Additional function layers

#### Circulation Workflow

**Check Out Process**:

**"To Patron" Subtab**:
1. Click Circulation tab
2. Select "To Patron" subtab
3. Identify patron (barcode or search)
4. Scan item barcodes sequentially
5. **Items Out section**: Real-time display of patron's loans

**Visual Feedback**:
- **All copies shown**: Complete loan list
- **Real-time updates**: Immediate confirmation
- **Clear organization**: Easy to scan visually

**Check In Process**:
- **Dedicated function**: Separate from checkout
- **Direct scanning**: Immediate barcode input
- **Return confirmation**: Clear success messages

#### Circulation Policies

**Configuration Access**:
- **Back Office → Library Policies → Circulation Types subtab**
- **Default settings**: System-assigned for new copies
- **Customizable rules**: Flexible policy management

**Policy Management**:
- **Edit existing**: Modify current policies
- **Create new**: Custom circulation types
- **Assign defaults**: Automatic application to items

#### Mobile and Remote Access

**Follett Destiny Mobile App**:
- **On-the-go operations**: Perform circulation anywhere
- **Patron status checks**: View account information
- **Item status queries**: Real-time availability

**VersaScan Integration**:
- **Real-time synchronization**: Immediate updates to Destiny
- **Circulation functions**: Full checkout/return support
- **Item and patron status**: Quick lookups
- **Inventory management**: Mobile inventory tools

#### Search Capabilities

**Multiple Search Modes**:
- **Item search**: Various criteria
- **Patron search**: Quick lookups
- **Status checks**: Real-time information

#### Notices and Communication

**Overdue Management**:
- **Email notices**: Automated reminders
- **Print notices**: Physical letters
- **Multiple email support**: Various addresses
- **Configurable templates**: Customizable messages

**Training and Support**:
- **Webinar essentials**: Structured training
- **Participant guides**: Documentation
- **Help documentation**: Comprehensive resources
- **Community forums**: User support

**Sources**:
- [Destiny Library Manager | Follett Software](https://follettsoftware.com/library-suite/destiny-library-manager/)
- [Circulation (Library Manager) - Destiny Help](https://legacyhelp.follettsoftware.com/content/c_circulation_LM.htm)
- [School Library Management Software | Follett Destiny](https://follettsoftware.com/library-suite/)

---

## 3. Cross-System UI Pattern Analysis

### 3.1 Circulation Workflow Patterns

#### Universal Two-Step Checkout Pattern

**Step 1: Identify Patron**
- Barcode scan or search by name
- Display patron information immediately
- Show warnings (overdue, at limit)
- Display current loans

**Step 2: Scan Items**
- Sequential barcode scanning
- Real-time confirmation for each item
- Running list of checked-out items
- Due date calculation and display

#### One-Step Return Pattern

**Direct Scanning**:
- No patron identification needed
- Scan item barcode directly
- Immediate return confirmation
- Display patron name and overdue status

#### Common UI Elements

**Patron Information Panel**:
- Name and ID
- Current loan count
- Overdue warnings (prominent, red)
- Contact information
- Checkout limits

**Item List Display**:
- Title
- Barcode
- Due date
- Status indicator
- Copy number

**Action Buttons**:
- Clear/New Transaction
- Print Receipt
- Email Receipt
- Cancel/Undo

**Sources**:
- [Library Management System Project | GeeksforGeeks](https://www.geeksforgeeks.org/software-engineering/library-management-system/)
- [A Comprehensive Guide to Library Management System Software](https://www.creatrixcampus.com/blog/library-management-system-software-guide)

---

### 3.2 Barcode Scanning Integration Patterns

#### Standard HID Keyboard Mode

**Universal Implementation**:
- Barcode scanners configured as HID (Human Interface Device) keyboards
- Emit regular keyboard input characters
- Automatically send Enter/Return key after barcode
- No special UI configuration needed

**UI Considerations**:
- **Auto-focus input fields**: Cursor ready for scanning
- **Enter key handling**: Submit on Enter
- **Error feedback**: Invalid barcode messages
- **Manual fallback**: Allow typing when scanner fails

#### Scanning Workflow

**Best Practices**:
1. **Point and shoot**: Simple trigger action
2. **Immediate feedback**: Visual/audio confirmation
3. **Database update**: Real-time status change
4. **Error handling**: Clear messages for unknown barcodes

**Speed and Accuracy**:
- **Quick transactions**: Seconds per item
- **Reduced errors**: Eliminates typing mistakes
- **Patron convenience**: Faster service
- **Real-time updates**: Immediate inventory changes

**Common Barcode Formats**:
- **Code 39**: Numbers and letters, popular in libraries
- **Codabar**: Numeric only
- **Code 128**: High density, more data

**Sources**:
- [Barcode Technology and its Application in Libraries](https://digitalcommons.unl.edu/cgi/viewcontent.cgi?article=6896&context=libphilprac)
- [Using Barcode for Library Management and Book Tracking](https://free-barcode.com/barcode/barcode-application/barcode-library-management-book-tracking.asp)
- [Self-checkout and Return System Solution for Libraries](https://www.lonvillscan.com/solutions/self-checkout-and-return-system-solution-for-libraries.html)

---

### 3.3 Catalog Search Interface Patterns

#### Search Interface Components

**Search Box**:
- **Prominent placement**: Top of page or dedicated search page
- **Auto-complete suggestions**: Dynamic dropdown
- **Search button**: Clear call-to-action
- **Advanced search link**: Optional detailed search

**Search Modes**:
- **Simple search**: Single box, all fields
- **Fielded search**: Specific field selection (title, author, ISBN, subject)
- **Barcode lookup**: Direct item or patron search
- **ISBN search**: Exact match priority

#### Faceted Search Implementation

**Benefits for Libraries**:
- **Faster searches**: Improve precision and recall
- **Better user experience**: More successful searches
- **Navigation aid**: Browse while searching
- **Progressive refinement**: Narrow results incrementally

**Challenges**:
- **Scale**: Large datasets require optimization
- **Metadata quality**: Depends on consistent, accurate facets
- **Resource diversity**: Different material types
- **Computational constraints**: Performance considerations
- **UI complexity**: Balance power with simplicity

**Facet Types**:
- **Availability**: Available, On loan, Reference only
- **Format**: Book, DVD, CD, Magazine, etc.
- **Subject**: Controlled vocabulary categories
- **Publication year**: Date ranges
- **Language**: Material language
- **Location**: Branch or shelf location

#### Auto-Complete Patterns

**Implementation**:
- **Search suggestions**: Dropdown under search field
- **Mobile optimization**: Especially useful on touch devices
- **Character-by-character**: Updates as user types
- **Selection shortcuts**: Click/tap to select suggestion
- **Keyboard navigation**: Arrow keys and Enter

**User Benefits**:
- **Faster queries**: Pick suggestion instead of typing
- **Spelling assistance**: Correct common errors
- **Discovery**: Suggest related terms
- **Mobile-friendly**: Reduce typing on small keyboards

#### Search Results Display

**Result List Components**:
- **Title and author**: Primary identifiers
- **Cover image**: Visual recognition (if available)
- **Publication info**: Year, publisher
- **Availability status**: Color-coded indicator
- **Format icon**: Book, DVD, etc.
- **Call number**: Shelf location

**Pagination**:
- **50 items per page**: Common standard
- **Page navigation**: Previous, Next, page numbers
- **Results count**: "Showing 1-50 of 237 results"
- **Jump to page**: Quick navigation

**Sorting Options**:
- **Relevance**: Default sort
- **Title A-Z**: Alphabetical
- **Publication date**: Newest first
- **Author**: Alphabetical by author

**Sources**:
- [Faceted Search Guide | Swiftype Documentation](https://swiftype.com/documentation/site-search/guides/faceted-search)
- [How to create a great faceted search and navigation experience](https://www.algolia.com/blog/ux/faceted-search-and-navigation)
- [Full article: Musings on Faceted Search, Metadata, and Library Discovery Interfaces](https://www.tandfonline.com/doi/full/10.1080/01639374.2023.2222120)
- [Create Search Suggestions Autocomplete - AddSearch](https://www.addsearch.com/docs/search-ui/autocomplete-suggestions/)

---

### 3.4 Navigation and Menu Structure

#### Module-Based Navigation Pattern

**Top-Level Structure**:
- **Persistent navigation bar**: Always visible
- **Module dropdown menus**: Grouped actions
- **Search bar**: Quick access to search
- **User menu**: Settings and logout

**Common Modules**:
1. **Circulation**: Checkout, Return, Renew
2. **Catalog**: Search, Browse, View details
3. **Patrons**: Search, Add, Edit, View history
4. **Cataloging**: Add records, Edit records, Import
5. **Reports**: Statistics, Overdue lists, Usage
6. **Administration**: Settings, Users, Policies

#### Breadcrumb Navigation

**Structure**:
- **Module name**: Top-level location
- **Page title**: Current page
- **Previous pages**: Path taken (optional)

**Example**: Circulation > Check Out > Patron Details

**Benefits**:
- **Orientation**: Users know where they are
- **Quick navigation**: Click to return to higher levels
- **Context**: Understand page relationship

#### Navigation Best Practices

**Menu Depth Guidelines**:
- **Maximum 2 tiers**: Simple dropdowns
- **3+ tiers**: Use mega menus or routing pages
- **Avoid deep nesting**: Frustrating for users

**Menu Types by Context**:
- **Light content**: Simple horizontal menus
- **Substantial content**: Mega menus
- **Mobile**: Hamburger menu acceptable
- **Desktop**: Visible navigation preferred

**Visibility and Consistency**:
- **Sticky navigation**: Remains visible when scrolling
- **Single menu system**: Avoid multiple different menus
- **Clear labels**: Avoid jargon, use plain language
- **Active page indication**: Highlight current location

**Accessibility**:
- **Large click targets**: Easy to click/tap
- **Adequate spacing**: Prevent accidental clicks
- **Keyboard navigation**: Tab through menu items
- **Screen reader support**: Proper ARIA labels

**Library-Specific Considerations**:
- **Room for growth**: Plan for content expansion
- **Task-oriented**: Organize by user goals, not system structure
- **Patron vs. Staff**: Different menus for different users
- **Frequent tasks first**: Prioritize common operations

**Sources**:
- [Navigation Best Practices for Your Library Website | Library Market](https://www.librarymarket.com/blog/navigation-best-practices-your-library-website)
- [Menu-Design Checklist: 17 UX Guidelines - NN/G](https://www.nngroup.com/articles/menu-design/)
- [Multilevel Menu Design Best Practices | Toptal](https://www.toptal.com/designers/ux/multilevel-menu-design)
- [UX best practices for designing a nav menu | Medium](https://uxtbe.medium.com/ux-best-practices-for-designing-a-nav-menu-0c125794fe08)

---

### 3.5 Borrower Management Patterns

#### List View

**Table Columns**:
- **Borrower ID**: Unique identifier
- **Name**: Last, First or First Last
- **Class/Grade**: Organizational unit
- **Current loans**: Count (e.g., "2/2")
- **Overdue**: Warning icon if applicable
- **Status**: Active/Inactive

**Filtering Options**:
- **Class filter**: Dropdown to select class
- **Status filter**: Active, Inactive, All
- **Overdue only**: Show only with overdue items
- **Search**: Name or ID search

#### Detail View

**Borrower Information**:
- **Personal details**: Name, ID, class, contact
- **Photo**: Optional borrower photo
- **Barcode**: Displayed for verification
- **Status**: Active/Inactive toggle

**Current Loans Section**:
- **Item list**: All checked-out items
- **Due dates**: Individual due dates
- **Renew buttons**: Quick renewal
- **Overdue highlighting**: Red text for late items

**Circulation History**:
- **Past loans**: Historical transactions
- **Date ranges**: Filter by date
- **Item details**: What was borrowed
- **Statistics**: Total checkouts, overdue count

**Actions**:
- **Edit information**: Update details
- **Check out items**: Quick link to circulation
- **Print ID card**: Generate barcode card
- **View fines**: If fee system implemented

---

### 3.6 Overdue Notices and Hold Workflows

#### Overdue Notice Patterns

**Notice Timing**:
- **1 week overdue**: First courtesy notice
- **2 weeks overdue**: Second reminder
- **4 weeks overdue**: Final notice/lost item

**Delivery Methods**:
- **Email**: Primary method
- **Print letters**: Backup/traditional
- **Phone lists**: Manual follow-up
- **Self-print**: Patron prints from account

**Notice Content**:
- **Borrower name**: Personalization
- **Item list**: Title, barcode, due date, days overdue
- **Instructions**: How to return/renew
- **Contact info**: Library phone/email

**Organization for Schools**:
- **One page per class**: Easy distribution to teachers
- **Grouped by homeroom**: Logical organization
- **Teacher copy**: For classroom follow-up
- **Summary statistics**: Total overdue by class

#### Hold Request Workflows

**Placing Holds**:
- **From catalog search**: "Place hold" button
- **Patron login required**: Identify requester
- **Email notification**: When item available
- **Hold shelf**: Physical location for pickups

**Hold Management**:
- **Hold queue**: Order of requests
- **Expiration date**: Auto-cancel if not picked up
- **Hold shelf report**: Items waiting for pickup
- **Notification methods**: Email, phone, SMS

**Patron Status Workflow**:
- **Requested**: Hold placed
- **In transit**: Moving to pickup location
- **On hold shelf**: Ready for pickup
- **Expired**: Not picked up in time
- **Cancelled**: Patron cancelled hold

**Sources**:
- [Overdue Notices - Evergreen - OWWL Docs](https://docs.owwl.org/Evergreen/OverdueNotices)
- [Notices, generating and sending | IFLS Library System](https://iflsweb.org/knowledge-base/notices)
- [Patron status workflows | Yale University Library](https://web.library.yale.edu/cataloging/catalog-maintenance-policies/item-withdrawl/patron-status-workflow)

---

## 4. Elementary School-Specific Patterns

### 4.1 Simplified Checkout for Children

**Low-Tech Approaches**:
- **Photo checkout**: Student takes photo with book
- **Clipboard log**: Simple paper sign-out sheet
- **Honor system**: Student responsibility

**Digital Solutions for Students**:

**QR Code Access**:
- **QR stickers**: On books or around library
- **Student devices**: Scan with phone/tablet
- **Checkout form**: Simple web form
- **Auto-populate data**: Student ID and book ID

**Booksource Classroom Platform** (Free):
- **Web-based**: No app download
- **Device agnostic**: iPad, Chromebook, phone
- **Student login**: Classroom ID + password
- **Class period selection**: Choose class
- **Name selection**: Pick from roster

**Google Sheets Integration**:
- **Automated data**: From checkout form
- **Student info**: Name and ID
- **Book ID**: Title or barcode
- **Checkout status**: Timestamp

#### Design Principles for Children

**Simplicity First**:
- "If it's simple, it's going to be easy for students to understand, easy to remember, and easy for parents to follow up with"
- **Minimal clicks**: 2-3 steps maximum
- **Large buttons**: Easy to tap/click
- **Visual cues**: Icons and colors
- **Clear language**: Grade-appropriate vocabulary

**Even Kindergarten Can Use**:
- Systems designed so young students can check out independently
- No librarian assistance required
- Build library independence early

**Sources**:
- [Easy Peasy Classroom Library Checkout System | Organized Classroom](https://organizedclassroom.com/easy-peasy-classroom-library-checkout-system/)
- [15 Classroom Library Checkout System Tips for Elementary Teachers](https://jodidurgin.com/classroom-library-checkout-system/)
- [Booksource Classroom: Free Library Checkout System - Write on With Miss G](https://writeonwithmissg.com/2022/07/26/booksource-classroom-all-about-this-free-library-checkout-system-part-1/)

---

### 4.2 BCD-Specific Considerations

**BCD Context** (Bibliothèque Centre Documentaire):

**Definition and Role**:
- **Pedagogical structure**: Integrated into preschool and primary schools
- **Learning promotion**: Foster reading and documentary research
- **Student participation**: Involve children in management
- **Official establishment**: Circular n° 84.360, October 1, 1984
- **Ministerial support**: Joint Ministry of Education and Culture

**Management Philosophy**:
- **Student involvement**: Book organization, lending assistance, order prep
- **Management committees**: Student-led governance
- **Reading committees**: Student input on collection
- **Sense of belonging**: Students help classmates find documents

**Software Solutions for BCD**:

**BCDI Software**:
- **Digital management**: Track loans digitally
- **User-friendly search**: Easy book discovery
- **Loan tracking**: Circulation management
- **Specialized for schools**: Designed for BCD context

**Biblioboost**:
- **Online BCD management**: Web-based platform
- **Student loans**: Circulation tracking
- **Reading quizzes**: Dynamic interactive quizzes
- **Dual interfaces**: Separate teacher and student views
- **Cloud-based**: Access from anywhere

**Interface Implications**:
- **Teacher/librarian view**: Full administrative access
- **Student view**: Simplified, age-appropriate interface
- **Pedagogical features**: Support learning objectives
- **French-first**: Primary language for interface

**Sources**:
- [BCD (bibliothèque centre documentaire) : concept et définition | Expodif](https://expodif.fr/conseils-et-ressources/bcd-bibliotheque-centre-documentaire-concept-et-definition/)
- [Biblioboost : logiciel de gestion de BCD en ligne](https://www.biblioboost.net/)
- [La BCD, une nécessité | Bulletin des bibliothèques de France](https://bbf.enssib.fr/consulter/bbf-1991-02-0120-005)

---

## 5. French Library Terminology

### 5.1 Core Circulation Terms

| English | French | Context |
|---------|--------|---------|
| Circulation | Prêt | General lending service |
| Loan/Checkout | Prêt | Act of checking out |
| Return | Retour | Returning items |
| Borrower | Emprunteur/Emprunteuse | Library patron |
| Circulation desk | Comptoir de prêt | Service point |
| Due date | Date de retour du prêt | When item is due back |
| Overdue | En retard | Past due date |
| Renew | Renouveler | Extend loan period |
| Hold/Reserve | Réservation | Request for item on loan |
| Recall | Rappeler | Request early return |

### 5.2 Collection and Cataloging Terms

| English | French | Context |
|---------|--------|---------|
| Bibliographic record | Notice bibliographique | Catalog record |
| Item/Copy | Exemplaire | Physical copy |
| Catalog | Catalogue | Collection database |
| ISBN | ISBN | International Standard Book Number |
| Barcode | Code-barres | Barcode label |
| Subject | Sujet | Topic/subject heading |
| Classification | Cote | Call number/shelf mark |

### 5.3 System and Administrative Terms

| English | French | Context |
|---------|--------|---------|
| Library management system | Système intégré de gestion de bibliothèque (SIGB) | ILS |
| Automated checkout | Automate de prêt-retour | Self-checkout machine |
| School library | BCD - Bibliothèque Centre Documentaire | Elementary school library |
| School documentation center | CDI - Centre de Documentation et d'Information | Secondary school library |
| Responsible for circulation | Responsable des prêts | Circulation staff |
| Borrowed | Emprunté | Checked out status |
| Academic year | Année scolaire | School year |
| Class | Classe | Grade/classroom group |

**Sources**:
- [library circulation - French translation – Linguee](https://www.linguee.com/english-french/translation/library+circulation.html)
- [French Definitions - Library Terminology - BYU](https://guides.lib.byu.edu/c.php?g=216485&p=1429236)
- [Quelle place pour les automates de prêt et de retour - ENSSIB](https://www.enssib.fr/bibliotheque-numerique/documents/962-quelle-place-pour-les-automates-de-pret-et-de-retour-dans-les-bibliotheques-publiques-francaises-analyse-technique-et-strategique.pdf)

---

## 6. Recommended UI Patterns for BCD Web UI

Based on the research findings, here are the recommended patterns to adopt for the BCD web UI:

### 6.1 Navigation Structure

**Recommended Approach**: Module-based navigation with maximum 2-tier depth

**Implementation**:
```
[BCD Logo] [Prêt/Retour] [Catalogue] [Emprunteurs] [Rapports] [Paramètres] [FR|EN]

Prêt/Retour dropdown:
  - Prêter (Check Out)
  - Retourner (Return)
  - Renouveler (Renew)

Catalogue dropdown:
  - Rechercher (Search)
  - Ajouter (Add - with ISBN lookup)
  - Parcourir (Browse)

Emprunteurs dropdown:
  - Rechercher (Search)
  - Lister par classe (List by Class)
  - Ajouter (Add)

Rapports dropdown:
  - En retard (Overdue)
  - Jamais empruntés (Never borrowed)
  - Plus empruntés (Most borrowed)

Paramètres dropdown:
  - Configuration (Settings)
  - À propos (About)
```

**Rationale**:
- Simple two-tier structure proven in Koha and Evergreen
- Organized by task/module (not system structure)
- French labels with English secondary
- Maximum 5-6 top-level items
- Dropdown shows max 4-5 options per module

---

### 6.2 Circulation Workflow

**Check Out (Prêter)**:

**Screen Layout**:
```
┌─────────────────────────────────────────────────────────┐
│ Prêt d'exemplaires                                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Emprunteur: [_________________] [Rechercher]             │
│                                                          │
│ ┌────────────────────────────────────────────────┐      │
│ │ BENALI Fatima (ID: 101)                         │      │
│ │ Classe: CP-A                                    │      │
│ │ Prêts en cours: 1/2                             │      │
│ └────────────────────────────────────────────────┘      │
│                                                          │
│ Exemplaire à prêter: [_________________]                 │
│ (Scanner le code-barres ou saisir manuellement)          │
│                                                          │
│ ┌────────────────────────────────────────────────┐      │
│ │ Exemplaires prêtés aujourd'hui:                 │      │
│ │ ✓ Le Petit Prince - À rendre le 13/02/2026     │      │
│ │ ✓ Charlotte's Web - À rendre le 13/02/2026     │      │
│ └────────────────────────────────────────────────┘      │
│                                                          │
│ [Nouveau prêt] [Imprimer reçu]                          │
└─────────────────────────────────────────────────────────┘
```

**Return (Retourner)**:

**Screen Layout**:
```
┌─────────────────────────────────────────────────────────┐
│ Retour d'exemplaires                                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Exemplaire: [_________________]                          │
│ (Scanner le code-barres)                                 │
│                                                          │
│ ┌────────────────────────────────────────────────┐      │
│ │ Retours d'aujourd'hui:                          │      │
│ │                                                 │      │
│ │ ✓ Le Petit Prince                               │      │
│ │   Emprunteur: BENALI Fatima (CP-A)              │      │
│ │   À temps ✓                                     │      │
│ │                                                 │      │
│ │ ✓ Stuart Little                                 │      │
│ │   Emprunteur: MARTIN Lucas (CP-B)               │      │
│ │   ⚠ EN RETARD (3 jours)                         │      │
│ └────────────────────────────────────────────────┘      │
│                                                          │
│ [Nouveau retour]                                         │
└─────────────────────────────────────────────────────────┘
```

**Key Features**:
- **Two-step checkout**: Patron first, then items
- **One-step return**: Direct item scanning
- **Real-time feedback**: Immediate confirmation
- **Visual warnings**: Red for overdue, yellow for at-limit
- **Auto-focus**: Input fields ready for scanner
- **Running list**: Shows completed transactions

---

### 6.3 Catalog Search

**Search Interface**:

```
┌─────────────────────────────────────────────────────────┐
│ Recherche du catalogue                                   │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Rechercher: [________________________] [Rechercher]      │
│                                                          │
│ Recherche avancée: [Titre ▼] [Auteur] [ISBN] [Sujet]   │
│                                                          │
│ Filtres: [○ Tous] [○ Disponibles seulement]            │
│                                                          │
│ ┌────────────────────────────────────────────────┐      │
│ │ Le Petit Prince                                 │      │
│ │ Saint-Exupéry, Antoine de (1943)                │      │
│ │ [●] Disponible  [●] Emprunté (retour: 13/02)   │ [>]  │
│ ├─────────────────────────────────────────────────┤      │
│ │ Charlotte's Web                                 │      │
│ │ White, E.B. (1952)                              │      │
│ │ [●] Disponible  [●] Disponible                 │ [>]  │
│ ├─────────────────────────────────────────────────┤      │
│ │ Stuart Little                                   │      │
│ │ White, E.B. (1945)                              │      │
│ │ [●] Emprunté (retour: 10/02)                    │ [>]  │
│ └────────────────────────────────────────────────┘      │
│                                                          │
│ Page 1 de 5  [<Précédent] [1] [2] [3] [4] [5] [Suivant>]│
└─────────────────────────────────────────────────────────┘
```

**Detail View** (when clicking [>]):

```
┌─────────────────────────────────────────────────────────┐
│ Le Petit Prince                                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Auteur: Saint-Exupéry, Antoine de                       │
│ ISBN: 9782070612758                                      │
│ Éditeur: Gallimard Jeunesse                              │
│ Année: 1943 (réédition 2007)                            │
│ Sujets: Fiction, Aventure, Classique                     │
│                                                          │
│ Résumé:                                                  │
│ Le récit des aventures d'un petit garçon venu           │
│ d'une autre planète...                                   │
│                                                          │
│ Exemplaires (2):                                         │
│ ┌────────────────────────────────────────────────┐      │
│ │ Ex. 1 - Code: 785                               │      │
│ │ [●] Disponible                                  │      │
│ │ Cote: F SAI                                     │      │
│ ├─────────────────────────────────────────────────┤      │
│ │ Ex. 2 - Code: 786                               │      │
│ │ [●] Emprunté - Retour: 13/02/2026               │      │
│ │ Emprunteur: BENALI Fatima (CP-A)                │      │
│ └────────────────────────────────────────────────┘      │
│                                                          │
│ [Retour aux résultats] [Modifier] [Ajouter exemplaire]  │
└─────────────────────────────────────────────────────────┘
```

**Key Features**:
- **Simple search box**: Prominent placement
- **Advanced options**: Expandable field selectors
- **Auto-complete**: As user types (future enhancement)
- **Color-coded status**: Green dot = available, Orange = on loan, Red = overdue
- **Pagination**: 50 results per page
- **Quick filters**: Available vs. All
- **Detail drill-down**: Click to see full record

---

### 6.4 Status Indicators and Color Coding

**Standard Color Scheme** (adopted across all systems):

| Status | Color | Icon | French Label | English Label |
|--------|-------|------|--------------|---------------|
| Available | Green (#28a745) | ● | Disponible | Available |
| On loan | Orange (#fd7e14) | ● | Emprunté | On loan |
| Overdue | Red (#dc3545) | ⚠ | En retard | Overdue |
| Lost | Gray (#6c757d) | ✗ | Perdu | Lost |
| Damaged | Yellow (#ffc107) | ⚠ | Endommagé | Damaged |

**Implementation**:
```css
.status-available { color: #28a745; }
.status-onloan { color: #fd7e14; }
.status-overdue { color: #dc3545; font-weight: bold; }
.status-lost { color: #6c757d; }
.status-damaged { color: #ffc107; }
```

**Usage Context**:
- **Search results**: Status badge next to each copy
- **Borrower view**: Highlight overdue items
- **Dashboard**: Summary statistics with colors
- **Reports**: Color-coded lists

---

### 6.5 Borrower Management

**List View**:

```
┌─────────────────────────────────────────────────────────┐
│ Emprunteurs                                              │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Classe: [Toutes ▼] [CP-A] [CP-B] [CE1-A] [CE1-B] ...   │
│                                                          │
│ Rechercher: [________________] [Rechercher]              │
│                                                          │
│ ┌────────────────────────────────────────────────┐      │
│ │ ID  │ Nom           │ Classe │ Prêts │ Retard │      │
│ ├─────┼───────────────┼────────┼───────┼────────┤      │
│ │ 101 │ BENALI Fatima │ CP-A   │ 2/2   │        │ [>]  │
│ │ 102 │ MARTIN Lucas  │ CP-B   │ 1/2   │ ⚠      │ [>]  │
│ │ 103 │ DUBOIS Emma   │ CP-A   │ 0/2   │        │ [>]  │
│ │ 104 │ BERNARD Tom   │ CE1-A  │ 2/2   │ ⚠⚠     │ [>]  │
│ └────────────────────────────────────────────────┘      │
│                                                          │
│ [Ajouter emprunteur] [Importer CSV]                     │
└─────────────────────────────────────────────────────────┘
```

**Detail View**:

```
┌─────────────────────────────────────────────────────────┐
│ BENALI Fatima                                            │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ ID: 101                    Code-barres: 00101            │
│ Classe: CP-A              Statut: [●] Actif              │
│                                                          │
│ Prêts en cours (2/2):                                    │
│ ┌────────────────────────────────────────────────┐      │
│ │ Le Petit Prince (785)                           │      │
│ │ Emprunté: 30/01/2026  Retour: 13/02/2026       │      │
│ │ [Renouveler]                                    │      │
│ ├─────────────────────────────────────────────────┤      │
│ │ Charlotte's Web (801)                           │      │
│ │ Emprunté: 25/01/2026  Retour: 08/02/2026       │      │
│ │ [Renouveler]                                    │      │
│ └────────────────────────────────────────────────┘      │
│                                                          │
│ Historique (10 derniers prêts):                         │
│ ┌────────────────────────────────────────────────┐      │
│ │ Stuart Little - 20/01/26 → 27/01/26 ✓          │      │
│ │ Matilda - 15/01/26 → 22/01/26 ✓                │      │
│ └────────────────────────────────────────────────┘      │
│                                                          │
│ [Modifier] [Prêter à cet emprunteur] [Imprimer carte]   │
└─────────────────────────────────────────────────────────┘
```

**Key Features**:
- **Class-based filtering**: Easy teacher distribution
- **Warning indicators**: Visual overdue alerts
- **Quick actions**: Direct links from list
- **Loan count**: X/Y format (current/limit)
- **History tracking**: Past circulation
- **Inline renewal**: Direct from borrower view

---

### 6.6 Cataloging with ISBN Lookup

**Add New Title**:

```
┌─────────────────────────────────────────────────────────┐
│ Ajouter au catalogue                                     │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ ISBN: [_________________] [Rechercher BNF]               │
│                                                          │
│ ┌────────────────────────────────────────────────┐      │
│ │ Données récupérées de la BNF:                   │      │
│ │                                                 │      │
│ │ Titre: [Le Petit Prince___________________]     │      │
│ │                                                 │      │
│ │ Auteur: [Saint-Exupéry, Antoine de________]    │      │
│ │                                                 │      │
│ │ Éditeur: [Gallimard Jeunesse______________]    │      │
│ │                                                 │      │
│ │ Année: [1943]  ISBN: [9782070612758]           │      │
│ │                                                 │      │
│ │ Sujets: [Fiction, Aventure, Classique_____]    │      │
│ │                                                 │      │
│ │ Résumé:                                         │      │
│ │ [_______________________________________]       │      │
│ │ [_______________________________________]       │      │
│ │                                                 │      │
│ └────────────────────────────────────────────────┘      │
│                                                          │
│ Exemplaire:                                              │
│ ┌────────────────────────────────────────────────┐      │
│ │ Code-barres: [Auto: 785____] ou [Manuel___]    │      │
│ │ Cote: [F SAI_____]                              │      │
│ │ État: [Bon ▼]                                   │      │
│ └────────────────────────────────────────────────┘      │
│                                                          │
│ [Enregistrer] [Annuler]                                  │
└─────────────────────────────────────────────────────────┘
```

**Workflow**:
1. Enter ISBN → Click "Rechercher BNF"
2. System retrieves data from BNF SRU API
3. Pre-populates form with retrieved data (editable)
4. Librarian reviews and edits if needed
5. System auto-generates item barcode (editable)
6. Click "Enregistrer" to save

**Error Handling**:
- **ISBN not found**: Allow manual entry in blank form
- **Duplicate ISBN**: Offer to add another copy instead
- **API timeout**: Show error, allow retry or manual entry

---

### 6.7 Reports Dashboard

**Overdue Report**:

```
┌─────────────────────────────────────────────────────────┐
│ Rapport des retards                                      │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ Classe: [Toutes ▼] [CP-A] [CP-B] [CE1-A] ...           │
│                                                          │
│ ┌────────────────────────────────────────────────┐      │
│ │ CP-A (3 exemplaires en retard)                  │      │
│ │                                                 │      │
│ │ BENALI Fatima (ID: 101)                         │      │
│ │   • Stuart Little (787) - 3 jours              │      │
│ │     Retour prévu: 27/01/2026                    │      │
│ │                                                 │      │
│ │ DUBOIS Emma (ID: 103)                           │      │
│ │   • Charlotte's Web (801) - 5 jours            │      │
│ │     Retour prévu: 25/01/2026                    │      │
│ │   • Matilda (812) - 2 jours                    │      │
│ │     Retour prévu: 28/01/2026                    │      │
│ └────────────────────────────────────────────────┘      │
│                                                          │
│ ┌────────────────────────────────────────────────┐      │
│ │ CP-B (1 exemplaire en retard)                   │      │
│ │                                                 │      │
│ │ MARTIN Lucas (ID: 102)                          │      │
│ │   • Le Petit Prince (785) - 1 jour             │      │
│ │     Retour prévu: 29/01/2026                    │      │
│ └────────────────────────────────────────────────┘      │
│                                                          │
│ [Imprimer] [Exporter PDF] [Email aux enseignants]       │
└─────────────────────────────────────────────────────────┘
```

**Most Borrowed Report**:

```
┌─────────────────────────────────────────────────────────┐
│ Titres les plus empruntés (Année scolaire 2025-2026)    │
├─────────────────────────────────────────────────────────┤
│                                                          │
│ ┌────────────────────────────────────────────────┐      │
│ │ 1. Charlotte's Web (E.B. White)                 │      │
│ │    ████████████████████████ 24 prêts            │      │
│ ├─────────────────────────────────────────────────┤      │
│ │ 2. Le Petit Prince (Saint-Exupéry)              │      │
│ │    ████████████████████ 22 prêts                │      │
│ ├─────────────────────────────────────────────────┤      │
│ │ 3. Matilda (Roald Dahl)                         │      │
│ │    ██████████████████ 20 prêts                  │      │
│ ├─────────────────────────────────────────────────┤      │
│ │ 4. Stuart Little (E.B. White)                   │      │
│ │    ████████████████ 18 prêts                    │      │
│ ├─────────────────────────────────────────────────┤      │
│ │ 5. Harry Potter à l'école (J.K. Rowling)        │      │
│ │    ██████████████ 16 prêts                      │      │
│ └────────────────────────────────────────────────┘      │
│                                                          │
│ [Imprimer] [Exporter CSV]                               │
└─────────────────────────────────────────────────────────┘
```

**Key Features**:
- **Class-based grouping**: Organized for teacher distribution
- **Print-optimized**: One page per class for overdue
- **Visual charts**: Bar charts for most borrowed
- **Export options**: PDF, CSV for further processing
- **Date-aware**: Academic year boundaries

---

### 6.8 Language Switching

**Implementation**:

**Top-right corner**:
```
[FR] | EN
```

**Active language**: Bold
**Click to switch**: Immediate UI update
**Preserve state**: Don't lose current page/data

**Date Formatting**:
- **French**: DD/MM/YYYY (30/01/2026)
- **English**: MM/DD/YYYY (01/30/2026)

**Number Formatting**:
- **French**: 1 234,56
- **English**: 1,234.56

**Translation File Structure**:
```javascript
// fr.json
{
  "circulation": {
    "checkout": "Prêter",
    "return": "Retourner",
    "renew": "Renouveler",
    "borrower": "Emprunteur",
    "item": "Exemplaire",
    "dueDate": "Date de retour",
    "overdue": "En retard"
  },
  "catalog": {
    "search": "Rechercher",
    "title": "Titre",
    "author": "Auteur",
    "available": "Disponible",
    "onLoan": "Emprunté"
  }
}

// en.json
{
  "circulation": {
    "checkout": "Check Out",
    "return": "Return",
    "renew": "Renew",
    "borrower": "Borrower",
    "item": "Item",
    "dueDate": "Due Date",
    "overdue": "Overdue"
  },
  "catalog": {
    "search": "Search",
    "title": "Title",
    "author": "Author",
    "available": "Available",
    "onLoan": "On Loan"
  }
}
```

---

## 7. Implementation Recommendations

### 7.1 Technology Stack (from spec requirements)

**No Build Tools Required**:
- **Vanilla JavaScript**: ES6+ features (arrow functions, async/await, fetch, modules)
- **CSS3**: Modern features (grid, flexbox, variables)
- **HTML5**: Semantic markup
- **No frameworks**: No React, Vue, Angular
- **No transpilation**: Direct browser support
- **No bundlers**: No webpack, Vite, etc.

**Browser Support**:
- **Chrome**: Latest 2 versions
- **Firefox**: Latest 2 versions
- **Safari**: Latest 2 versions
- **Edge**: Latest 2 versions

### 7.2 Performance Targets

**Response Times**:
- **Page load**: < 3 seconds
- **Search results**: < 2 seconds
- **Circulation operations**: < 1 second
- **Navigation**: < 100ms (SPA instant feel)

**Loading Indicators**:
- **Show spinner**: After 500ms for API calls
- **Disable buttons**: Prevent double-submission
- **Progress feedback**: For long operations

### 7.3 Accessibility Considerations

**Keyboard Navigation**:
- **Tab order**: Logical flow through forms
- **Enter to submit**: Standard form behavior
- **Escape to cancel**: Close modals/dialogs
- **Arrow keys**: Navigate lists/menus

**Screen Readers**:
- **Semantic HTML**: Proper heading hierarchy
- **ARIA labels**: For icons and controls
- **Status announcements**: For dynamic updates
- **Skip links**: Jump to main content

**Visual**:
- **Color contrast**: WCAG AA minimum (4.5:1)
- **Large click targets**: 44x44px minimum
- **Clear focus indicators**: Visible keyboard focus
- **Scalable text**: Support browser zoom

### 7.4 Mobile Responsiveness

**Breakpoints**:
- **Desktop**: 1024px and up (primary target)
- **Tablet**: 768px - 1023px (secondary)
- **Mobile**: Below 768px (nice-to-have, not priority)

**Layout Adaptations**:
- **Stacked forms**: Vertical layout on smaller screens
- **Collapsible navigation**: Hamburger menu on mobile
- **Touch-friendly**: Larger buttons and spacing
- **Simplified tables**: Responsive table patterns

---

## 8. Key Takeaways for BCD Implementation

### What to Adopt

1. **Module-based navigation**: Clear, simple menu structure with 2-tier maximum depth
2. **Two-step checkout, one-step return**: Universal pattern that works
3. **Color-coded status**: Green/Orange/Red for Available/On loan/Overdue
4. **Auto-focus input fields**: Ready for barcode scanning immediately
5. **Real-time feedback**: Confirm each action instantly
6. **Class-based organization**: Perfect for school context
7. **Print-optimized reports**: One page per class for overdue notices
8. **French-first interface**: Primary language with English toggle
9. **Simple, uncluttered design**: Minimize clicks for common operations
10. **Responsive design**: Support desktop and tablet devices

### What to Avoid

1. **Deep menu hierarchies**: Keep navigation shallow (max 2 levels)
2. **Complex faceted search**: Start simple, add later if needed
3. **Heavy JavaScript frameworks**: Vanilla JS sufficient for this scale
4. **Overcomplicated workflows**: Elementary librarians need speed
5. **Too many visual elements**: White space and simplicity win
6. **Ambiguous status indicators**: Use universally understood colors
7. **Pagination overload**: 50 items per page is standard
8. **Confusing terminology**: Use standard library terms in French
9. **Mobile-first design**: Desktop is primary for librarians
10. **Feature creep**: Focus on core circulation and catalog functions

### Success Metrics

1. **Checkout in under 30 seconds**: Including borrower lookup and 2 items
2. **Return in under 20 seconds**: Process 5 items
3. **Search results in under 2 seconds**: For 5,000 item catalog
4. **3 clicks or less**: For common tasks from homepage
5. **99% scanner compatibility**: Standard HID keyboard mode
6. **Zero training time**: Intuitive enough for first-time use
7. **Works on existing hardware**: No special requirements
8. **Teacher satisfaction**: Easy to distribute overdue notices by class
9. **Student engagement**: Clear status, easy to understand
10. **Librarian efficiency**: Faster than CLI for daily operations

---

## References

### Open-Source Systems
- [Koha Community](https://koha-community.org/)
- [Koha Interface Patterns Wiki](https://wiki.koha-community.org/wiki/Interface_patterns)
- [Evergreen ILS](https://evergreen-ils.org/)
- [Evergreen UI Style Guide](https://evergreen-ils.org/documentation/previews/proposed_style_guide.html)
- [OPALS](https://opalsinfo.net/)

### Commercial Systems
- [Alexandria Library Software](https://www.goalexandria.com/)
- [Follett Destiny Library Manager](https://follettsoftware.com/library-suite/destiny-library-manager/)

### UX and Design Resources
- [Navigation Best Practices - Library Market](https://www.librarymarket.com/blog/navigation-best-practices-your-library-website)
- [Menu Design Guidelines - Nielsen Norman Group](https://www.nngroup.com/articles/menu-design/)
- [Faceted Search Guide - Algolia](https://www.algolia.com/blog/ux/faceted-search-and-navigation)

### French Library Resources
- [BCD Definition - Expodif](https://expodif.fr/conseils-et-ressources/bcd-bibliotheque-centre-documentaire-concept-et-definition/)
- [Biblioboost - Logiciel BCD](https://www.biblioboost.net/)
- [Koha France - Association KohaLa](https://koha-fr.org/)

### Barcode and Hardware
- [Barcode Technology in Libraries](https://digitalcommons.unl.edu/cgi/viewcontent.cgi?article=6896&context=libphilprac)
- [Self-checkout Solutions - Lonvill Scan](https://www.lonvillscan.com/solutions/self-checkout-and-return-system-solution-for-libraries.html)

### School Library Patterns
- [Elementary School Library Organization](https://organizedclassroom.com/easy-peasy-classroom-library-checkout-system/)
- [Classroom Library Checkout Tips](https://jodidurgin.com/classroom-library-checkout-system/)

---

**Document Version**: 1.0
**Last Updated**: 2026-01-30
**Next Review**: Before UI implementation begins
