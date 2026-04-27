"""Simulate a screening dialog in text — no telephony, no DB.

Usage:
    python scripts/simulate_dialog.py --phone=+79991234567 --scenario=courier_screening

Прогоняет DialogSession по списку заранее заготовленных ответов кандидата
и печатает реплики агента. Полезно, чтобы быстро проверить FSM после правок
в app/core/dialog.py без реального звонка.
"""

from __future__ import annotations

import argparse

import structlog

from app.core.dialog import DialogSession
from app.core.scenario import load_template_yaml

log = structlog.get_logger()


def run_simulation(phone: str, scenario_slug: str) -> None:
    scenario = load_template_yaml(scenario_slug)
    if scenario is None:
        raise SystemExit(f"scenario template '{scenario_slug}' not found in scenarios/")

    log.info("simulate_start", phone=phone, scenario=scenario_slug)

    session = DialogSession(scenario)
    greeting = session.get_greeting()
    log.info("agent_greeting", text=greeting)

    test_responses = [
        "Да, согласен",
        "Да, работал курьером в Яндекс.Еде полгода",
        "Полная занятость",
        "Есть велосипед",
        "Да, есть медкнижка",
        "Готов с понедельника",
        "Центральный район",
    ]

    for response in test_responses:
        if session.finished:
            break
        log.info("candidate_says", text=response)
        reply = session.process_candidate_reply(response)
        if reply is None:
            log.info("conversation_ended")
            break
        log.info("agent_says", text=reply)

    transcript = session.get_transcript()
    log.info(
        "simulate_complete",
        turns=len(transcript),
        unclear=sorted(session.unclear_indices),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="VoiceScreen dialog simulation")
    parser.add_argument("--phone", required=True, help="Phone number (только для лога)")
    parser.add_argument("--scenario", default="courier_screening", help="Scenario slug")
    args = parser.parse_args()

    run_simulation(args.phone, args.scenario)


if __name__ == "__main__":
    main()
