"""Test call script — make a debug screening call to a phone number.

Usage:
    python scripts/test_call.py --phone=+79991234567 --scenario=courier_screening
"""

import argparse
import asyncio

import structlog

log = structlog.get_logger()


async def run_test_call(phone: str, scenario: str) -> None:
    from app.core.dialog import DialogSession

    log.info("test_call_start", phone=phone, scenario=scenario)

    session = DialogSession(scenario)
    greeting = await session.get_greeting()
    log.info("agent_greeting", text=greeting)

    # In a real test, this would go through Mango telephony.
    # For now, simulate a text-based conversation.
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
        log.info("candidate_says", text=response)
        reply = await session.process_candidate_reply(response)
        if reply is None:
            log.info("conversation_ended")
            break
        log.info("agent_says", text=reply)

    transcript = session.get_transcript()
    log.info("test_call_complete", turns=len(transcript))


def main() -> None:
    parser = argparse.ArgumentParser(description="VoiceScreen test call")
    parser.add_argument("--phone", required=True, help="Phone number to call")
    parser.add_argument("--scenario", default="courier_screening", help="Scenario name")
    args = parser.parse_args()

    asyncio.run(run_test_call(args.phone, args.scenario))


if __name__ == "__main__":
    main()
