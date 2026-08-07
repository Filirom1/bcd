from src.bcd_api.services.inventory._policy import (
    can_deaccession,
    item_update_decision,
)


def test_item_update_decision():
    # has_active_loan=False, updates={"status": "in_repair", "condition": "damaged"}
    decision = item_update_decision(
        has_active_loan=False,
        requested_updates={"status": "in_repair", "condition": "damaged"},
    )
    assert decision.accepted_updates == {"status": "in_repair", "condition": "damaged"}
    assert decision.ignored_fields == ()

    # has_active_loan=True, updates={"status": "in_repair", "condition": "damaged"}
    decision = item_update_decision(
        has_active_loan=True,
        requested_updates={"status": "in_repair", "condition": "damaged"},
    )
    assert decision.accepted_updates == {"condition": "damaged"}
    assert decision.ignored_fields == ("status",)

    # has_active_loan=True, updates={"condition": "damaged"}
    decision = item_update_decision(
        has_active_loan=True,
        requested_updates={"condition": "damaged"},
    )
    assert decision.accepted_updates == {"condition": "damaged"}
    assert decision.ignored_fields == ()

    # has_active_loan=False, updates={}
    decision = item_update_decision(has_active_loan=False, requested_updates={})
    assert decision.accepted_updates == {}
    assert decision.ignored_fields == ()


def test_can_deaccession():
    assert can_deaccession(has_active_loan=True) is False
    assert can_deaccession(has_active_loan=False) is True
