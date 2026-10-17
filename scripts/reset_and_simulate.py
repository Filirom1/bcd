#!/usr/bin/env python3
"""
Reset database and simulate library activity from September 2016 through today.

This script:
1. Resets database using Alembic migrations
2. Imports catalog from catalog_dublin_core.csv
3. Imports students from students_import.csv
4. Simulates activity from Sep 2016 through the current date

Scheduling: two balanced cohorts of classes alternate weekly. Each attending class
visits in two half-class sessions; returns are processed before parallel checkouts.

Uses function-scoped imports to avoid SQLAlchemy metadata conflicts.
"""

import csv
import random
import subprocess
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta


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


def initialize_system_settings(session, today):
    """Create SystemSettings singleton with loan_limit_default=2."""
    # Import models HERE (inside function)
    from src.bcd_api.models.system_settings import SystemSettings

    school_year = _school_year_start(today)
    settings = SystemSettings(
        id=1,
        library_name="BCD École Primaire",
        loan_duration_days=14,
        loan_limit_default=2,
        loan_limit_teacher=10,
        hold_expiration_days=15,
        academic_year_current=f"{school_year}-{school_year + 1}",
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

    print("✓ Catalog imported:")
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

    # Average age per grade level (French primary school)
    grade_ages = {'CP': 6, 'CE1': 7, 'CE2': 8, 'CM1': 9, 'CM2': 10}

    classes = {}
    for class_name in sorted(set(class_names)):
        grade = class_name.split('-')[0]
        class_obj = Class(
            name=class_name,
            notes="Imported from students CSV",
            average_age=grade_ages.get(grade),
        )
        session.add(class_obj)
        classes[class_name] = class_obj

    session.commit()
    print(f"✓ Created {len(classes)} classes: {', '.join(sorted(classes.keys()))}")
    return classes


def recount_student_counts(session, classes):
    """Update the denormalized student_count on each class after bulk import."""
    from src.bcd_api.models.borrower import Borrower

    for class_obj in classes.values():
        count = session.query(Borrower).filter(
            Borrower.class_id == class_obj.id
        ).count()
        class_obj.student_count = count

    session.commit()
    total = sum(c.student_count for c in classes.values())
    print(f"✓ Student counts updated ({total} students across {len(classes)} classes)")


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


def _school_year_start(day):
    return day.year if day.month >= 9 else day.year - 1


def _is_approximate_school_break(day):
    """Approximate Zone A breaks; exact Friday dates remain real calendar dates."""
    return (
        day.month in (7, 8)
        or (day.month == 10 and day.day >= 20)
        or (day.month == 11 and day.day <= 5)
        or (day.month == 12 and day.day >= 20)
        or (day.month == 1 and day.day <= 5)
        or (day.month == 2 and day.day >= 15)
        or (day.month == 3 and day.day <= 1)
        or (day.month == 4 and 10 <= day.day <= 30)
    )


def _is_french_public_holiday(day):
    return (day.month, day.day) in {
        (1, 1),
        (5, 1),
        (5, 8),
        (7, 14),
        (8, 15),
        (11, 1),
        (11, 11),
        (12, 25),
    }


def _school_fridays(start_date, end_date):
    first_friday = start_date + timedelta(days=(4 - start_date.weekday()) % 7)
    fridays = []
    current = first_friday
    while current <= end_date:
        if not _is_approximate_school_break(current) and not _is_french_public_holiday(current):
            fridays.append(current)
        current += timedelta(days=7)
    return first_friday, fridays


def _advance_student_roster(
    session, classes, cp_class_sizes, first_names, last_names, next_numeric_id, rng, effective_at
):
    from src.bcd_api.models.borrower import Borrower

    grade_order = ("CP", "CE1", "CE2", "CM1", "CM2")
    class_by_id = {class_obj.id: class_obj for class_obj in classes.values()}
    classes_by_grade = defaultdict(list)
    student_counts = Counter()
    for class_obj in classes.values():
        grade = class_obj.name.split("-", 1)[0]
        classes_by_grade[grade].append(class_obj)

    students = session.query(Borrower).filter(
        Borrower.role == "student", Borrower.active.is_(True)
    ).all()
    graduating_count = 0
    for student in students:
        current_class = class_by_id.get(student.class_id)
        if not current_class:
            continue
        student_counts[current_class.id] += 1
        grade = current_class.name.split("-", 1)[0]
        if grade not in grade_order:
            continue
        if grade == "CM2":
            student.active = False
            student.updated_at = effective_at
            graduating_count += 1
            continue

        next_grade = grade_order[grade_order.index(grade) + 1]
        section = current_class.name.split("-", 1)[1] if "-" in current_class.name else None
        candidates = classes_by_grade.get(next_grade, [])
        if not candidates:
            continue
        matching_section = [
            class_obj
            for class_obj in candidates
            if section is not None
            and "-" in class_obj.name
            and class_obj.name.split("-", 1)[1] == section
        ]
        target = min(
            matching_section or candidates,
            key=lambda class_obj: (student_counts[class_obj.id], class_obj.name),
        )
        student_counts[current_class.id] -= 1
        student_counts[target.id] += 1
        student.class_id = target.id
        student.grade_level = next_grade
        student.updated_at = effective_at

    active_names = {
        student.full_name
        for student in session.query(Borrower).filter(
            Borrower.role == "student", Borrower.active.is_(True)
        )
    }
    if graduating_count and not cp_class_sizes:
        raise RuntimeError("Cannot replace graduating students without a CP class")

    new_students_by_cp_class = Counter()
    for _ in range(graduating_count):
        target_class = min(
            cp_class_sizes,
            key=lambda class_name: (
                new_students_by_cp_class[class_name] / cp_class_sizes[class_name],
                class_name,
            ),
        )
        new_students_by_cp_class[target_class] += 1

    for class_name, count in new_students_by_cp_class.items():
        class_obj = classes[class_name]
        for _ in range(count):
            full_name = None
            for _attempt in range(100):
                first_name = rng.choice(first_names)
                last_name = rng.choice(last_names)
                candidate_name = f"{first_name} {last_name}"
                if candidate_name not in active_names:
                    full_name = candidate_name
                    break
            if full_name is None:
                full_name = f"{rng.choice(first_names)} {rng.choice(last_names)}"
            if next_numeric_id > 999999:
                raise RuntimeError("Generated student IDs exceed the configured six-digit limit")

            first_name, last_name = full_name.split(" ", 1)
            session.add(
                Borrower(
                    borrower_id=str(next_numeric_id),
                    first_name=first_name,
                    last_name=last_name,
                    full_name=full_name,
                    role="student",
                    class_id=class_obj.id,
                    grade_level="CP",
                    active=True,
                    created_at=effective_at,
                    updated_at=effective_at,
                )
            )
            next_numeric_id += 1
            active_names.add(full_name)

    session.flush()
    return next_numeric_id


def _mark_school_year_losses(
    session,
    school_year_start,
    rng,
    active_holds_by_record,
    loaned_count_by_record,
    missed_return_visits,
    deferred_return_ids,
    stats,
):
    from src.bcd_api.models.circulation import CirculationTransaction
    from src.bcd_api.models.item import Item

    year_start = datetime.combine(date(school_year_start, 9, 1), time.min)
    next_year_start = datetime.combine(date(school_year_start + 1, 9, 1), time.min)
    candidates = (
        session.query(CirculationTransaction, Item)
        .join(Item, Item.id == CirculationTransaction.item_id)
        .filter(
            CirculationTransaction.checkout_date >= year_start,
            CirculationTransaction.checkout_date < next_year_start,
            CirculationTransaction.return_date.is_(None),
            Item.status == "on_loan",
            Item.loanable.is_(True),
        )
        .all()
    )
    candidates = [
        (loan, item)
        for loan, item in candidates
        if not active_holds_by_record.get(item.bibliographic_record_id)
        and missed_return_visits.get(loan.id, 0) == 0
        and loan.id not in deferred_return_ids
    ]
    count = min(10, len(candidates))
    if count < 10:
        print(
            f"ℹ Only {count} eligible books available to mark lost for "
            f"school year {school_year_start}-{school_year_start + 1}"
        )

    for loan, item in rng.sample(candidates, count):
        item.status = "lost"
        item.loanable = False
        loan.notes = "Définitivement perdu dans la simulation"
        loaned_count_by_record[item.bibliographic_record_id] -= 1
        missed_return_visits.pop(loan.id, None)
        deferred_return_ids.discard(loan.id)
        stats["losses"] += 1

    session.flush()


def simulate_activity(session, start_date, end_date, seed=42):
    """Simulate real-date circulation, class visits, reservations, and annual losses."""
    from sqlalchemy import func

    from src.bcd_api.models.borrower import Borrower
    from src.bcd_api.models.circulation import CirculationTransaction
    from src.bcd_api.models.class_model import Class
    from src.bcd_api.models.hold import Hold
    from src.bcd_api.models.item import Item
    from src.bcd_api.models.system_settings import SystemSettings
    from src.bcd_api.services.holds._queue import (
        next_waiting_hold,
        reorder_after_removal_in_transaction,
    )
    from src.bcd_api.services.holds.commands import (
        create_hold_in_transaction,
        fulfill_hold_in_transaction,
        mark_hold_ready_in_transaction,
    )

    rng = random.Random(seed)
    first_friday, fridays = _school_fridays(start_date, end_date)
    settings = session.query(SystemSettings).first()
    if settings is None:
        raise RuntimeError("System settings must be initialized before simulating activity")

    all_classes = session.query(Class).order_by(Class.name).all()
    classes = {class_obj.name: class_obj for class_obj in all_classes}
    class_names = sorted(classes)
    class_cohort = {name: index % 2 for index, name in enumerate(class_names)}
    class_teacher = {
        class_obj.name: class_obj.homeroom_teacher or "Équipe BCD"
        for class_obj in all_classes
    }

    initial_students = session.query(Borrower).filter(Borrower.role == "student").all()
    cp_class_sizes = Counter(
        student.class_.name
        for student in initial_students
        if student.active and student.class_ and student.class_.name.startswith("CP")
    )
    first_names = sorted({student.first_name for student in initial_students})
    last_names = sorted({student.last_name for student in initial_students})
    numeric_ids = [
        int(student.borrower_id)
        for student in initial_students
        if student.borrower_id.isdigit()
    ]
    next_numeric_id = max(numeric_ids, default=0) + 1

    items = session.query(Item).all()
    available_by_record = defaultdict(dict)
    loaned_count_by_record = Counter()
    for item in items:
        if item.loanable and item.status == "available":
            available_by_record[item.bibliographic_record_id][item.id] = item
        elif item.status == "on_loan":
            loaned_count_by_record[item.bibliographic_record_id] += 1

    active_loan_count = Counter()
    for borrower_id, count in (
        session.query(
            CirculationTransaction.borrower_id,
            func.count(CirculationTransaction.id),
        )
        .filter(CirculationTransaction.return_date.is_(None))
        .group_by(CirculationTransaction.borrower_id)
        .all()
    ):
        active_loan_count[borrower_id] = count

    active_holds_by_record = defaultdict(list)
    active_holds_by_borrower = Counter()
    ready_holds_by_borrower = defaultdict(list)
    waiting_hold_count_by_record = Counter()
    for hold in session.query(Hold).filter(Hold.status.in_(("waiting", "ready"))).all():
        active_holds_by_record[hold.bibliographic_record_id].append(hold)
        active_holds_by_borrower[hold.borrower_id] += 1
        if hold.status == "ready":
            ready_holds_by_borrower[hold.borrower_id].append(hold)
        else:
            waiting_hold_count_by_record[hold.bibliographic_record_id] += 1

    missed_return_visits = {}
    deferred_return_ids = set()
    pending_missed_return_visits = {}
    stats = {
        "checkouts": 0,
        "returns": 0,
        "late_returns": 0,
        "forgotten_books": 0,
        "holds_placed": 0,
        "holds_picked_up": 0,
        "losses": 0,
    }
    current_school_year = _school_year_start(start_date)

    def make_checkout(student, item, checkout_at, teacher_name, picked_up_hold=None):
        transaction = CirculationTransaction(
            borrower_id=student.id,
            item_id=item.id,
            bibliographic_record_id=item.bibliographic_record_id,
            checkout_date=checkout_at,
            due_date=checkout_at.date() + timedelta(days=settings.loan_duration_days),
            checked_out_by=teacher_name,
            status="active",
            renewal_count=0,
        )
        session.add(transaction)
        item.status = "on_loan"
        item.last_borrowed_at = checkout_at
        available_by_record[item.bibliographic_record_id].pop(item.id, None)
        loaned_count_by_record[item.bibliographic_record_id] += 1
        active_loan_count[student.id] += 1
        stats["checkouts"] += 1
        missed_visits = 1 if rng.random() < 0.05 else 0
        pending_missed_return_visits[transaction] = missed_visits
        if missed_visits:
            stats["forgotten_books"] += 1

        if picked_up_hold is not None:
            fulfill_hold_in_transaction(session, picked_up_hold.id)
            active_holds_by_borrower[student.id] -= 1
            active_holds_by_record[item.bibliographic_record_id].remove(picked_up_hold)
            ready_holds_by_borrower[student.id].remove(picked_up_hold)
            stats["holds_picked_up"] += 1
            promote_available_holds(item.bibliographic_record_id, checkout_at)
        return transaction

    def promote_available_holds(record_id, available_at):
        ready_for_record = [
            hold
            for hold in active_holds_by_record[record_id]
            if hold.status == "ready"
        ]
        available_count = len(available_by_record[record_id])
        while (
            len(ready_for_record) < available_count
            and waiting_hold_count_by_record[record_id] > 0
        ):
            hold = next_waiting_hold(session, record_id)
            if hold is None:
                break
            waiting_hold_count_by_record[record_id] -= 1
            ready_hold = mark_hold_ready_in_transaction(
                session, hold.id, expiration_days=settings.hold_expiration_days
            )
            ready_hold.available_date = available_at
            ready_hold.expiration_date = (
                available_at.date() + timedelta(days=settings.hold_expiration_days)
            )
            ready_for_record.append(ready_hold)
            ready_holds_by_borrower[ready_hold.borrower_id].append(ready_hold)
            session.flush()

    def expire_simulated_holds(friday):
        expired_holds = (
            session.query(Hold)
            .filter(
                Hold.status == "ready",
                Hold.expiration_date.isnot(None),
                Hold.expiration_date < friday,
            )
            .all()
        )
        for hold in expired_holds:
            record_id = hold.bibliographic_record_id
            active_holds_by_record[record_id].remove(hold)
            active_holds_by_borrower[hold.borrower_id] -= 1
            ready_holds_by_borrower[hold.borrower_id].remove(hold)
            reorder_after_removal_in_transaction(session, record_id, hold.queue_position)
            session.delete(hold)
        if expired_holds:
            session.flush()
            for record_id in {hold.bibliographic_record_id for hold in expired_holds}:
                promote_available_holds(record_id, datetime.combine(friday, time(9, 0)))

    print(f"\nSimulation from {start_date} through {end_date} (seed={seed})...")
    print("=" * 60)
    print(f"Active classes: {', '.join(class_names)}")
    print(f"School Fridays (approximate Zone A holidays): {len(fridays)}")
    print(
        "Class cohorts: "
        + ", ".join(
            f"{'A' if class_cohort[name] == 0 else 'B'}={name}"
            for name in class_names
        )
    )
    print("=" * 60)

    for friday in fridays:
        school_year = _school_year_start(friday)
        if school_year != current_school_year:
            school_year_end = date(current_school_year + 1, 9, 1) - timedelta(days=1)
            if end_date >= school_year_end:
                _mark_school_year_losses(
                    session,
                    current_school_year,
                    rng,
                    active_holds_by_record,
                    loaned_count_by_record,
                    missed_return_visits,
                    deferred_return_ids,
                    stats,
                )
            effective_at = datetime.combine(date(school_year, 9, 1), time(8, 0))
            next_numeric_id = _advance_student_roster(
                session,
                classes,
                cp_class_sizes,
                first_names,
                last_names,
                next_numeric_id,
                rng,
                effective_at,
            )
            current_school_year = school_year
            print(
                f"--- {school_year}-{school_year + 1} --- "
                f"checkouts: {stats['checkouts']}, returns: {stats['returns']}, "
                f"losses: {stats['losses']}"
            )

        expire_simulated_holds(friday)
        week_index = (friday - first_friday).days // 7
        cohort = week_index % 2
        active_students = session.query(Borrower).filter(
            Borrower.role == "student", Borrower.active.is_(True)
        ).all()
        students_by_class_id = defaultdict(list)
        for student in active_students:
            if student.class_id is not None:
                students_by_class_id[student.class_id].append(student)

        visiting_classes = [
            class_name
            for class_name in class_names
            if class_cohort[class_name] == cohort
            and students_by_class_id.get(classes[class_name].id)
        ]
        session_index = 0

        for class_name in visiting_classes:
            class_obj = classes[class_name]
            students = sorted(
                students_by_class_id[class_obj.id], key=lambda student: student.borrower_id
            )
            midpoint = (len(students) + 1) // 2
            subgroups = (students[:midpoint], students[midpoint:])

            for subgroup in subgroups:
                if not subgroup:
                    continue

                group_start = datetime.combine(friday, time(9, 0)) + timedelta(
                    minutes=session_index * 25
                )
                session_index += 1
                teacher_name = class_teacher[class_name]
                student_ids = [student.id for student in subgroup]
                due_loans = (
                    session.query(CirculationTransaction, Item)
                    .join(Item, Item.id == CirculationTransaction.item_id)
                    .filter(
                        CirculationTransaction.borrower_id.in_(student_ids),
                        CirculationTransaction.return_date.is_(None),
                        CirculationTransaction.due_date <= friday,
                        Item.status == "on_loan",
                    )
                    .order_by(
                        CirculationTransaction.checkout_date,
                        CirculationTransaction.id,
                    )
                    .all()
                )

                return_index = 0
                for loan, item in due_loans:
                    if missed_return_visits.get(loan.id, 0):
                        missed_return_visits[loan.id] -= 1
                        deferred_return_ids.add(loan.id)
                        continue
                    if loan.id not in deferred_return_ids and friday > loan.due_date:
                        loan.due_date = friday
                    returned_at = group_start + timedelta(seconds=15 * return_index)
                    return_index += 1
                    loan.return_date = returned_at
                    loan.returned_by = teacher_name
                    loan.status = "returned"
                    item.status = "available"
                    available_by_record[item.bibliographic_record_id][item.id] = item
                    loaned_count_by_record[item.bibliographic_record_id] -= 1
                    active_loan_count[loan.borrower_id] -= 1
                    stats["returns"] += 1
                    if returned_at.date() > loan.due_date:
                        stats["late_returns"] += 1
                    missed_return_visits.pop(loan.id, None)
                    deferred_return_ids.discard(loan.id)
                    promote_available_holds(item.bibliographic_record_id, returned_at)

                session.flush()

                available_by_record_for_group = {
                    record_id: sorted(copies.values(), key=lambda item: item.id)
                    for record_id, copies in available_by_record.items()
                    if copies
                }
                reserved_items_by_hold = {}
                for record_id, holds in active_holds_by_record.items():
                    ready_holds = sorted(
                        (hold for hold in holds if hold.status == "ready"),
                        key=lambda hold: (hold.queue_position, hold.id),
                    )
                    copies = available_by_record_for_group.get(record_id, [])
                    for hold, item in zip(ready_holds, copies):
                        reserved_items_by_hold[hold.id] = item
                reserved_item_ids = {
                    item.id for item in reserved_items_by_hold.values()
                }
                general_available = [
                    item
                    for copies in available_by_record_for_group.values()
                    for item in copies
                    if item.id not in reserved_item_ids
                ]

                checkout_start = group_start + timedelta(
                    seconds=max(180, return_index * 15 + 30)
                )
                for student in subgroup:
                    checkout_at = checkout_start + timedelta(seconds=rng.randint(0, 240))
                    max_to_borrow = max(0, 2 - active_loan_count[student.id])
                    if max_to_borrow:
                        ready_holds = sorted(
                            ready_holds_by_borrower[student.id],
                            key=lambda hold: (hold.available_date, hold.id),
                        )
                        for hold in ready_holds:
                            if max_to_borrow <= 0:
                                break
                            if hold.available_date.date() >= friday:
                                continue
                            item = reserved_items_by_hold.get(hold.id)
                            if item is None:
                                continue
                            make_checkout(
                                student,
                                item,
                                checkout_at,
                                teacher_name,
                                picked_up_hold=hold,
                            )
                            reserved_items_by_hold.pop(hold.id, None)
                            reserved_item_ids.discard(item.id)
                            max_to_borrow -= 1

                        if general_available and rng.random() <= 0.80 and max_to_borrow:
                            desired_count = min(
                                rng.randint(1, 2), max_to_borrow, len(general_available)
                            )
                            for _ in range(desired_count):
                                popular_threshold = max(1, len(general_available) // 5)
                                if rng.random() < 0.60 and len(general_available) >= popular_threshold:
                                    item = general_available[
                                        rng.randrange(min(popular_threshold, len(general_available)))
                                    ]
                                else:
                                    item = rng.choice(general_available)
                                general_available.remove(item)
                                make_checkout(student, item, checkout_at, teacher_name)
                                max_to_borrow -= 1

                    if (
                        rng.random() < 0.10
                        and active_holds_by_borrower[student.id]
                        < settings.max_holds_per_borrower
                    ):
                        unavailable_records = [
                            record_id
                            for record_id, loaned_count in loaned_count_by_record.items()
                            if loaned_count > 0
                            and not available_by_record[record_id]
                            and not any(
                                hold.borrower_id == student.id
                                and hold.status in ("waiting", "ready")
                                for hold in active_holds_by_record[record_id]
                            )
                        ]
                        if unavailable_records:
                            record_id = rng.choice(unavailable_records)
                            hold = create_hold_in_transaction(
                                session,
                                student.id,
                                record_id,
                                created_by=teacher_name,
                                notes="Réservation simulée : titre déjà emprunté",
                            )
                            hold.hold_date = checkout_at
                            hold.created_at = checkout_at
                            hold.updated_at = checkout_at
                            active_holds_by_record[record_id].append(hold)
                            active_holds_by_borrower[student.id] += 1
                            waiting_hold_count_by_record[record_id] += 1
                            stats["holds_placed"] += 1

                session.flush()
                for transaction, missed_visits in pending_missed_return_visits.items():
                    missed_return_visits[transaction.id] = missed_visits
                pending_missed_return_visits.clear()

        session.flush()

    _mark_school_year_losses(
        session,
        current_school_year,
        rng,
        active_holds_by_record,
        loaned_count_by_record,
        missed_return_visits,
        deferred_return_ids,
        stats,
    )
    session.commit()

    print("\n" + "=" * 60)
    print("SIMULATION COMPLETE")
    print("=" * 60)
    print(f"Total checkouts:      {stats['checkouts']:5d}")
    print(f"Total returns:        {stats['returns']:5d}")
    print(f"Late returns:         {stats['late_returns']:5d}")
    print(f"Forgotten books:      {stats['forgotten_books']:5d}")
    print(f"Holds placed/picked:  {stats['holds_placed']:5d}/{stats['holds_picked_up']}")
    print(f"Books lost:           {stats['losses']:5d}")

    active = session.query(CirculationTransaction).filter(
        CirculationTransaction.return_date.is_(None)
    ).count()
    overdue = session.query(CirculationTransaction).filter(
        CirculationTransaction.return_date.is_(None),
        CirculationTransaction.due_date < end_date,
    ).count()
    print(f"\nCurrently on loan or lost: {active}")
    print(f"Overdue as of {end_date}: {overdue}")

    top_books = (
        session.query(
            Item.item_id,
            func.count(CirculationTransaction.id).label("borrow_count"),
        )
        .join(CirculationTransaction, Item.id == CirculationTransaction.item_id)
        .group_by(Item.item_id)
        .order_by(func.count(CirculationTransaction.id).desc())
        .limit(5)
        .all()
    )
    if top_books:
        print("\nTop 5 most borrowed items:")
        for item_id, count in top_books:
            print(f"  {item_id}: {count} times")
    print("=" * 60)


def create_teachers_and_staff(session, classes):
    """Create 1 teacher per class, 1 directeur, and 2 blocked borrowers."""
    from src.bcd_api.models.borrower import Borrower
    from src.shared.constants import BorrowerRole

    # Realistic French teacher names — one per class (sorted alphabetical class order)
    teacher_data = [
        ("Sophie",    "Martin",    "Mme Martin"),
        ("Pierre",    "Bernard",   "M. Bernard"),
        ("Claire",    "Dupont",    "Mme Dupont"),
        ("François",  "Simon",     "M. Simon"),
        ("Nathalie",  "Leroy",     "Mme Leroy"),
        ("Julien",    "Moreau",    "M. Moreau"),
        ("Marie",     "Petit",     "Mme Petit"),
        ("Isabelle",  "Lambert",   "Mme Lambert"),
        ("Thomas",    "Rousseau",  "M. Rousseau"),
    ]

    class_list = list(classes.values())
    teachers = []

    for i, class_obj in enumerate(class_list):
        grade = class_obj.name.split('-')[0] if '-' in class_obj.name else class_obj.name
        first, last, display = teacher_data[i] if i < len(teacher_data) else (f"Enseignant{i+1}", class_obj.name, f"Ens. {class_obj.name}")
        teacher = Borrower(
            borrower_id=f"T{100 + i:03d}",
            first_name=first,
            last_name=last.upper(),
            full_name=f"{first} {last.upper()}",
            role=BorrowerRole.TEACHER.value,
            class_id=class_obj.id,
            grade_level=grade,
            active=True,
        )
        session.add(teacher)
        teachers.append(teacher)
        # Update class homeroom_teacher field
        class_obj.homeroom_teacher = display

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

    session.commit()
    total = len(teachers) + 1 + 2  # teachers + directeur + 2 blocked
    print(f"✓ Created teachers and staff ({total} borrowers)")
    return teachers


def diversify_item_statuses(session):
    """Mark 3 items in repair and 1 reference copy, without inventing extra losses."""
    from src.bcd_api.models.circulation import CirculationTransaction
    from src.bcd_api.models.item import Item
    from src.shared.constants import ItemStatus

    on_loan_ids = session.query(CirculationTransaction.item_id).filter(
        CirculationTransaction.return_date.is_(None)
    ).scalar_subquery()

    candidates = session.query(Item).filter(
        Item.id.notin_(on_loan_ids),
        Item.loanable.is_(True),
    ).order_by(Item.id.desc()).limit(4).all()

    if len(candidates) < 4:
        print("ℹ Not enough available items to diversify statuses — skipping")
        return

    for item in candidates[:3]:
        item.status = ItemStatus.IN_REPAIR.value
        item.loanable = False

    candidates[3].loanable = False  # reference copy, status stays available

    session.commit()
    print("✓ Diversified item statuses (3 in_repair, 1 reference)")


def create_demo_holds(session, today):
    """Create 4 demo holds: 2 waiting, 1 ready, 1 expired."""
    from datetime import datetime, timezone

    from src.bcd_api.models.borrower import Borrower
    from src.bcd_api.models.hold import Hold
    from src.bcd_api.models.item import Item
    from src.shared.constants import HoldStatus

    borrowers = session.query(Borrower).filter(Borrower.active.is_(True)).limit(4).all()
    if len(borrowers) < 4:
        print("ℹ Not enough borrowers for demo holds — skipping")
        return

    on_loan_item = session.query(Item).filter(Item.status == "on_loan").first()
    available_item = session.query(Item).filter(
        Item.status == "available", Item.loanable.is_(True)
    ).first()
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
    from src.bcd_api.models.circulation import CirculationTransaction
    from src.bcd_api.models.item import Item

    borrowers = session.query(Borrower).filter(Borrower.active.is_(True)).limit(5).all()
    items = session.query(Item).filter(
        Item.loanable.is_(True), Item.status == "available"
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
    database_url = f"sqlite:///{project_root / 'data' / 'bcd.db'}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False}
    )
    session_local = sessionmaker(bind=engine)
    session = session_local()

    try:
        simulation_end = date.today()

        # Step 3: Initialize settings
        print("Step 2: Initializing system settings...")
        initialize_system_settings(session, simulation_end)
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
        recount_student_counts(session, classes)
        print()

        # Step 8: Create teachers before simulation so each action records the teacher.
        print("Step 6: Creating teachers and staff...")
        create_teachers_and_staff(session, classes)
        print()

        # Step 9: Simulate activity through the current date.
        print(f"Step 7: Simulating library activity through {simulation_end}...")
        simulate_activity(
            session,
            start_date=date(2016, 9, 2),
            end_date=simulation_end,
            seed=42,
        )
        print()

        # Step 10: Diversify remaining item statuses for realistic screenshots.
        print("Step 8: Diversifying item statuses...")
        diversify_item_statuses(session)

        print("\n✓ Simulation completed successfully!")
        print("\nNext steps:")
        print("  1. Start API server: uvicorn src.bcd_api.main:app --host 127.0.0.1 --port 8000")
        print("  2. Start web UI: python -m src.bcd_web.server")
        print("  3. Open browser: http://localhost:8888/")

    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        session.close()


if __name__ == "__main__":
    main()
