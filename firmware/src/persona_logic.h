#pragma once

#include <stdint.h>

enum PersonaState : uint8_t { P_SLEEP, P_IDLE, P_BUSY, P_ATTENTION, P_CELEBRATE, P_DIZZY, P_HEART };

struct PersonaInputs {
  bool connected;
  uint8_t sessionsRunning;
  uint8_t sessionsWaiting;
};

// Bridge-driven base state only. One-shot effects like celebrate, dizzy,
// and heart are layered separately in the main loop.
inline PersonaState derivePersonaState(const PersonaInputs& input) {
  if (!input.connected) return P_SLEEP;
  if (input.sessionsWaiting > 0) return P_ATTENTION;
  if (input.sessionsRunning > 0) return P_BUSY;
  return P_IDLE;
}
