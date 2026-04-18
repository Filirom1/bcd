#!/usr/bin/env python3
"""
Reset database and simulate 9 months of library activity.

This script:
1. Resets database using Alembic migrations
2. Imports catalog from catalog_dublin_core.csv
3. Imports students from students_import.csv
4. Simulates 9 months of activity (Sep 2024 - May 2025)

Uses function-scoped imports to avoid SQLAlchemy metadata conflicts.
"""

import subprocess
import sys
from pathlib import Path
from datetime import date, timedelta
import random
import csv


def reset_database(project_root):
    """Reset database by deleting and recreating via Alembic."""
    db_file = project_root / "data" / "bcd.db"
    if db_file.exists():
        db_file.unlink()
        print("✓ Database file deleted")
    else:
        print("ℹ No existing database file")

    result = subprocess.run(["alembic", "upgrade", "head"],
                          capture_output=True, text=True, cwd=project_root)
    if result.returncode != 0:
        print(f"✗ Alembic migration failed:\n{result.stderr}")
        sys.exit(1)
    print("✓ Database recreated via migrations")


def initialize_system_settings(session):
    """Create SystemSettings singleton with loan_limit_default=2."""
    # Import models HERE (inside function)
    from src.bcd_api.models.system_settings import SystemSettings

    settings = SystemSettings(
        id=1,
        library_name="BCD École Primaire",
        loan_duration_days=14,
        loan_limit_default=2,
        loan_limit_teacher=10,
        academic_year_current="2024-2025",
        id_format="numeric",
        id_validation_regex=r"^\d{3,6}$"
    )
    session.add(settings)
    session.commit()
    print(f"✓ System settings initialized (loan_limit_default={settings.loan_limit_default})")
    return settings


def import_catalog(session, project_root):
    """Import catalog using dublin_core_import service."""
    # Import service HERE
    from src.bcd_api.services.dublin_core_import import import_dublin_core_csv

    catalog_path = project_root / "data/sample_imports/catalog_dublin_core.csv"
    if not catalog_path.exists():
        print(f"✗ Catalog file not found: {catalog_path}")
        sys.exit(1)

    with open(catalog_path, 'r', encoding='utf-8') as f:
        csv_content = f.read()

    print(f"ℹ Importing catalog from {catalog_path}...")
    result = import_dublin_core_csv(session, csv_content)

    print(f"✓ Catalog imported:")
    print(f"  - Bibliographic records: {result.records_created}")
    print(f"  - Items created: {result.items_created}")
    if result.errors:
        print(f"  - Errors: {len(result.errors)}")
        for error in result.errors[:5]:  # Show first 5 errors
            print(f"    • {error}")

    return result


def create_classes(session, class_names):
    """Create Class objects for each unique class name."""
    # Import Class model HERE
    from src.bcd_api.models.class_model import Class

    classes = {}
    for class_name in sorted(set(class_names)):
        class_obj = Class(
            name=class_name,
            notes="Imported from students CSV"
        )
        session.add(class_obj)
        classes[class_name] = class_obj

    session.commit()
    print(f"✓ Created {len(classes)} classes: {', '.join(sorted(classes.keys()))}")
    return classes


def import_students(session, classes, project_root):
    """Import students from CSV."""
    # Import Borrower model HERE
    from src.bcd_api.models.borrower import Borrower
    from src.shared.constants import BorrowerRole

    students_path = project_root / "data/sample_imports/students_import.csv"
    if not students_path.exists():
        print(f"✗ Students file not found: {students_path}")
        sys.exit(1)

    borrowers = []
    blocked_count = 0

    with open(students_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            class_obj = classes.get(row['Class'])
            is_blocked = bool(row.get('BlockReason', '').strip())

            borrower = Borrower(
                borrower_id=row['StudentID'],
                first_name=row['FirstName'],
                last_name=row['LastName'],
                full_name=f"{row['FirstName']} {row['LastName']}",
                role=BorrowerRole.STUDENT.value,
                class_id=class_obj.id if class_obj else None,
                grade_level=(class_obj.name.split('-')[0] if class_obj and '-' in class_obj.name else class_obj.name if class_obj else None),
                active=not is_blocked,
                blocked_reason=row.get('BlockReason', '').strip() or None,
            )
            borrowers.append(borrower)
            if is_blocked:
                blocked_count += 1

    # Bulk insert
    session.add_all(borrowers)
    session.commit()
    print(f"✓ Imported {len(borrowers)} students ({blocked_count} blocked)")
    return borrowers


def simulate_activity(session, start_date, months=9):
    """Simulate library activity over 9 months."""
    # Import models HERE
    from src.bcd_api.models.borrower import Borrower
    from src.bcd_api.models.class_model import Class
    from src.bcd_api.models.item import Item
    from src.bcd_api.models.circulation import CirculationTransaction

    print(f"\nℹ Starting simulation from {start_date} for {months} months...")
    print("=" * 60)

    # Statistics tracking
    stats = {
        'checkouts': 0,
        'returns': 0,
        'late_returns': 0,
        'renewals': 0
    }

    # Get all Fridays in period
    fridays = []
    current = start_date
    end = start_date + timedelta(days=months * 30)
    while current <= end:
        if current.weekday() == 4:  # Friday
            fridays.append(current)
        current += timedelta(days=1)

    print(f"ℹ Generated {len(fridays)} Fridays for simulation")

    # Group students by class
    students_by_class = {}
    all_classes = session.query(Class).order_by(Class.name).all()

    for class_obj in all_classes:
        students = session.query(Borrower).filter(
            Borrower.class_id == class_obj.id,
            Borrower.active == True
        ).all()
        if students:
            students_by_class[class_obj.name] = students

    class_names = sorted(students_by_class.keys())
    print(f"ℹ Active classes: {', '.join(class_names)}")
    print(f"ℹ Total active students: {sum(len(s) for s in students_by_class.values())}")

    # Get all available items at start
    total_items = session.query(Item).filter(Item.loanable == True).count()
    print(f"ℹ Total loanable items: {total_items}")
    print("=" * 60)

    # Simulate each Friday
    for week_idx, friday in enumerate(fridays):
        # Determine visiting class (rotate every 2 weeks)
        class_idx = (week_idx // 2) % len(class_names)
        class_name = class_names[class_idx]

        # Determine visiting half (alternate weekly)
        half = week_idx % 2
        students = students_by_class[class_name]
        half_size = len(students) // 2
        visiting = students[:half_size] if half == 0 else students[half_size:]

        # === RETURNS: Process due items ===
        active_loans = session.query(CirculationTransaction).filter(
            CirculationTransaction.return_date.is_(None),
            CirculationTransaction.due_date <= friday
        ).all()

        for loan in active_loans:
            if random.random() < 0.90:  # 90% on time
                # Return on due date or 1-2 days early
                days_early = random.randint(0, 2)
                return_date = loan.due_date - timedelta(days=days_early)
            else:  # 10% late
                # Return 1-7 days late
                days_late = random.randint(1, 7)
                return_date = loan.due_date + timedelta(days=days_late)
                stats['late_returns'] += 1

            loan.return_date = return_date
            loan.returned_by = "Librarian"

            # Update item status
            item = session.get(Item, loan.item_id)
            item.status = "available"
            stats['returns'] += 1

        session.commit()

        # === RENEWALS: 15% of items due in next 7 days ===
        upcoming = session.query(CirculationTransaction).filter(
            CirculationTransaction.return_date.is_(None),
            CirculationTransaction.due_date > friday,
            CirculationTransaction.due_date <= friday + timedelta(days=7)
        ).all()

        for loan in upcoming:
            if random.random() < 0.15:
                loan.due_date = loan.due_date + timedelta(days=14)
                loan.renewal_count = (loan.renewal_count or 0) + 1
                stats['renewals'] += 1

        session.commit()

        # === CHECKOUTS: 80% of visiting students borrow 1-2 books ===
        available = session.query(Item).filter(
            Item.loanable == True,
            Item.status == "available"
        ).all()

        if not available:
            print(f"Week {week_idx + 1} ({friday}): {class_name} (half {half + 1}) - No books available!")
            continue

        for student in visiting:
            # 80% chance student borrows
            if random.random() > 0.80:
                continue

            # Check how many books student currently has out
            current_loans = session.query(CirculationTransaction).filter(
                CirculationTransaction.borrower_id == student.id,
                CirculationTransaction.return_date.is_(None)
            ).count()

            # Respect loan limit (default 2)
            max_to_borrow = 2 - current_loans
            if max_to_borrow <= 0:
                continue

            # Random 1-2 books (respecting limit)
            num_to_borrow = min(random.randint(1, 2), max_to_borrow)

            if len(available) < num_to_borrow:
                num_to_borrow = len(available)

            if num_to_borrow == 0:
                continue

            # Select items (popular books 60% of the time)
            # Popular = first 20% of available list
            popular_threshold = max(1, len(available) // 5)
            borrowed = []

            for _ in range(num_to_borrow):
                if random.random() < 0.60 and len(available) >= popular_threshold:
                    # Pick from popular books
                    idx = random.randint(0, min(popular_threshold - 1, len(available) - 1))
                    item = available[idx]
                else:
                    # Pick random book
                    item = random.choice(available)

                borrowed.append(item)
                available.remove(item)

            # Create transactions
            for item in borrowed:
                due_date = friday + timedelta(days=14)
                transaction = CirculationTransaction(
                    borrower_id=student.id,
                    item_id=item.id,
                    bibliographic_record_id=item.bibliographic_record_id,
                    checkout_date=friday,
                    due_date=due_date,
                    checked_out_by="Librarian",
                    status="active",
                    renewal_count=0
                )
                session.add(transaction)
                item.status = "on_loan"
                stats['checkouts'] += 1

        session.commit()

        # Print progress
        active_count = session.query(CirculationTransaction).filter(
            CirculationTransaction.return_date.is_(None)
        ).count()

        print(f"Week {week_idx + 1:2d} ({friday}): {class_name:6s} (half {half + 1}) - "
              f"Active loans: {active_count:3d}, Available: {len(available):4d}")

    # === FINAL STATISTICS ===
    print("\n" + "=" * 60)
    print("📊 SIMULATION COMPLETE")
    print("=" * 60)
    print(f"Total checkouts:  {stats['checkouts']:4d}")
    print(f"Total returns:    {stats['returns']:4d}")
    print(f"Late returns:     {stats['late_returns']:4d} ({stats['late_returns']/max(stats['returns'],1)*100:.1f}%)")
    print(f"Renewals:         {stats['renewals']:4d}")

    active = session.query(CirculationTransaction).filter(
        CirculationTransaction.return_date.is_(None)
    ).count()
    print(f"\nCurrently on loan: {active}")

    overdue = session.query(CirculationTransaction).filter(
        CirculationTransaction.return_date.is_(None),
        CirculationTransaction.due_date < date.today()
    ).count()
    print(f"Currently overdue: {overdue}")

    # Most borrowed books
    from sqlalchemy import func
    top_books = session.query(
        Item.item_id,
        func.count(CirculationTransaction.id).label('borrow_count')
    ).join(
        CirculationTransaction, Item.id == CirculationTransaction.item_id
    ).group_by(
        Item.item_id
    ).order_by(
        func.count(CirculationTransaction.id).desc()
    ).limit(5).all()

    if top_books:
        print("\nTop 5 most borrowed items:")
        for item_id, count in top_books:
            print(f"  {item_id}: {count} times")

    print("=" * 60)


def create_teachers_and_staff(session, classes):
    """Create 1 teacher per class, 1 directeur, 2 blocked borrowers, 3 active loans for first teacher."""
    from src.bcd_api.models.borrower import Borrower
    from src.bcd_api.models.circulation import CirculationTransaction
    from src.bcd_api.models.item import Item
    from src.shared.constants import BorrowerRole

    class_list = list(classes.values())
    teachers = []

    for i, class_obj in enumerate(class_list):
        grade = class_obj.name.split('-')[0] if '-' in class_obj.name else class_obj.name
        teacher = Borrower(
            borrower_id=f"T{100 + i:03d}",
            first_name=f"Enseignant{i + 1}",
            last_name=class_obj.name,
            full_name=f"Enseignant{i + 1} {class_obj.name}",
            role=BorrowerRole.TEACHER.value,
            class_id=class_obj.id,
            grade_level=grade,
            active=True,
        )
        session.add(teacher)
        teachers.append(teacher)

    directeur = Borrower(
        borrower_id="DIR001",
        first_name="Directeur",
        last_name="École",
        full_name="Directeur École",
        role=BorrowerRole.STAFF.value,
        active=True,
    )
    session.add(directeur)

    blocked1 = Borrower(
        borrower_id="BLK001",
        first_name="Martin",
        last_name="Bloqué",
        full_name="Martin Bloqué",
        role=BorrowerRole.STUDENT.value,
        class_id=class_list[0].id if class_list else None,
        active=False,
        blocked_reason="Livre perdu non remboursé",
    )
    blocked2 = Borrower(
        borrower_id="BLK002",
        first_name="Sophie",
        last_name="Bloquée",
        full_name="Sophie Bloquée",
        role=BorrowerRole.STUDENT.value,
        class_id=class_list[1].id if len(class_list) > 1 else (class_list[0].id if class_list else None),
        active=False,
        blocked_reason="Trop de retards répétés",
    )
    session.add(blocked1)
    session.add(blocked2)
    session.flush()

    # 3 active loans for the first teacher
    if teachers:
        teacher = teachers[0]
        items = session.query(Item).filter(
            Item.loanable == True,
            Item.status == "available"
        ).limit(3).all()
        today = date.today()
        for item in items:
            tx = CirculationTransaction(
                borrower_id=teacher.id,
                item_id=item.id,
                bibliographic_record_id=item.bibliographic_record_id,
                checkout_date=today - timedelta(days=7),
                due_date=today + timedelta(days=7),
                checked_out_by="Librarian",
                status="active",
                renewal_count=0,
            )
            session.add(tx)
            item.status = "on_loan"

    session.commit()
    total = len(teachers) + 1 + 2  # teachers + directeur + 2 blocked
    print(f"✓ Created teachers and staff ({total} borrowers)")
    return teachers


def diversify_item_statuses(session):
    """Mark 3 items in_repair, 2 lost, 1 reference (loanable=False) — all from non-loaned items."""
    from src.bcd_api.models.item import Item
    from src.bcd_api.models.circulation import CirculationTransaction
    from src.shared.constants import ItemStatus

    on_loan_ids = session.query(CirculationTransaction.item_id).filter(
        CirculationTransaction.return_date.is_(None)
    ).scalar_subquery()

    candidates = session.query(Item).filter(
        Item.id.notin_(on_loan_ids),
        Item.loanable == True,
    ).order_by(Item.id.desc()).limit(6).all()

    if len(candidates) < 6:
        print("ℹ Not enough available items to diversify statuses — skipping")
        return

    for item in candidates[:3]:
        item.status = ItemStatus.IN_REPAIR.value
        item.loanable = False

    for item in candidates[3:5]:
        item.status = ItemStatus.LOST.value
        item.loanable = False

    candidates[5].loanable = False  # reference copy, status stays available

    session.commit()
    print("✓ Diversified item statuses (2 lost, 3 in_repair, 1 reference)")


def create_demo_holds(session, today):
    """Create 4 demo holds: 2 waiting, 1 ready, 1 expired."""
    from src.bcd_api.models.hold import Hold
    from src.bcd_api.models.borrower import Borrower
    from src.bcd_api.models.item import Item
    from src.shared.constants import HoldStatus
    from datetime import datetime, timezone

    borrowers = session.query(Borrower).filter(Borrower.active == True).limit(4).all()
    if len(borrowers) < 4:
        print("ℹ Not enough borrowers for demo holds — skipping")
        return

    on_loan_item = session.query(Item).filter(Item.status == "on_loan").first()
    available_item = session.query(Item).filter(Item.status == "available", Item.loanable == True).first()
    if not on_loan_item or not available_item:
        print("ℹ Missing on-loan or available item for demo holds — skipping")
        return

    holds = [
        Hold(borrower_id=borrowers[0].id, bibliographic_record_id=on_loan_item.bibliographic_record_id,
             queue_position=1, status=HoldStatus.WAITING.value, created_by="Librarian"),
        Hold(borrower_id=borrowers[1].id, bibliographic_record_id=available_item.bibliographic_record_id,
             queue_position=1, status=HoldStatus.READY.value,
             expiration_date=today + timedelta(days=2),
             available_date=datetime.now(timezone.utc), created_by="Librarian"),
        Hold(borrower_id=borrowers[2].id, bibliographic_record_id=on_loan_item.bibliographic_record_id,
             queue_position=2, status=HoldStatus.WAITING.value, created_by="Librarian"),
        Hold(borrower_id=borrowers[3].id, bibliographic_record_id=available_item.bibliographic_record_id,
             queue_position=1, status=HoldStatus.CANCELLED.value, created_by="Librarian"),
    ]
    session.add_all(holds)
    session.commit()
    print("✓ Created demo holds (waiting: 2, ready: 1, cancelled: 1)")


def create_demo_current_loans(session, today):
    """Create 5 demo active loans with varied states: overdue, due today, upcoming, renewed ×1, renewed ×2."""
    from src.bcd_api.models.borrower import Borrower
    from src.bcd_api.models.item import Item
    from src.bcd_api.models.circulation import CirculationTransaction

    borrowers = session.query(Borrower).filter(Borrower.active == True).limit(5).all()
    items = session.query(Item).filter(
        Item.loanable == True, Item.status == "available"
    ).limit(5).all()

    if len(borrowers) < 5 or len(items) < 5:
        print("ℹ Not enough borrowers or items for demo current loans — skipping")
        return

    scenarios = [
        dict(checkout_date=today - timedelta(days=19), due_date=today - timedelta(days=5), renewal_count=0),  # overdue
        dict(checkout_date=today - timedelta(days=14), due_date=today, renewal_count=0),                      # due today
        dict(checkout_date=today - timedelta(days=12), due_date=today + timedelta(days=2), renewal_count=0),  # upcoming
        dict(checkout_date=today - timedelta(days=21), due_date=today + timedelta(days=7), renewal_count=1),  # renewed ×1
        dict(checkout_date=today - timedelta(days=35), due_date=today + timedelta(days=14), renewal_count=2), # renewed ×2
    ]

    for borrower, item, kwargs in zip(borrowers, items, scenarios):
        tx = CirculationTransaction(
            borrower_id=borrower.id,
            item_id=item.id,
            bibliographic_record_id=item.bibliographic_record_id,
            checked_out_by="Librarian",
            status="active",
            **kwargs,
        )
        session.add(tx)
        item.status = "on_loan"

    session.commit()
    overdue = sum(1 for s in scenarios if s["due_date"] < today)
    renewed = sum(1 for s in scenarios if s["renewal_count"] > 0)
    at_limit = sum(1 for b in borrowers if session.query(CirculationTransaction).filter(
        CirculationTransaction.borrower_id == b.id,
        CirculationTransaction.return_date.is_(None)
    ).count() >= 2)
    print(f"✓ Created demo current loans (overdue: {overdue}, renewed: {renewed}, at-limit: {at_limit})")


def main():
    """Main workflow."""
    import sys
    from pathlib import Path

    # Add project root to path (script is in scripts/ subdirectory)
    project_root = Path(__file__).parent.parent
    sys.path.insert(0, str(project_root))

    print("=" * 60)
    print("BCD Database Reset & Activity Simulation")
    print("=" * 60)
    print()

    # Step 1: Reset database
    print("Step 1: Resetting database...")
    reset_database(project_root)
    print()

    # Step 2: Import database utilities (AFTER reset, BEFORE creating session)
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    # Create engine and session
    DATABASE_URL = f"sqlite:///{project_root / 'data' / 'bcd.db'}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False}
    )
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        # Step 3: Initialize settings
        print("Step 2: Initializing system settings...")
        initialize_system_settings(session)
        print()

        # Step 4: Import catalog
        print("Step 3: Importing catalog...")
        import_catalog(session, project_root)
        print()

        # Step 5: Read students CSV for class names
        print("Step 4: Creating classes...")
        students_path = project_root / "data/sample_imports/students_import.csv"
        with open(students_path, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            class_names = [row['Class'] for row in reader]

        # Step 6: Create classes
        classes = create_classes(session, class_names)
        print()

        # Step 7: Import students
        print("Step 5: Importing students...")
        import_students(session, classes, project_root)
        print()

        # Step 8: Simulate activity
        print("Step 6: Simulating 9 months of library activity...")
        start_date = date(2024, 9, 6)  # First Friday in September 2024
        simulate_activity(session, start_date, months=9)
        print()

        # Step 9: Add teachers, staff, and blocked borrowers
        print("Step 7: Creating teachers and staff...")
        create_teachers_and_staff(session, classes)

        # Step 10: Diversify item statuses for realistic screenshots
        print("Step 8: Diversifying item statuses...")
        diversify_item_statuses(session)

        # Step 11: Create demo holds
        print("Step 9: Creating demo holds...")
        create_demo_holds(session, date.today())

        # Step 12: Create demo current loans
        print("Step 10: Creating demo current loans...")
        create_demo_current_loans(session, date.today())

        print("\n✓ Simulation completed successfully!")
        print("\nNext steps:")
        print("  1. Start API server: uvicorn src.bcd_api.main:app --host 127.0.0.1 --port 8000")
        print("  2. Start web UI: python -m src.bcd_web.server")
        print("  3. Open browser: http://localhost:8000/")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
