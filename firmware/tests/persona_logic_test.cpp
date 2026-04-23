#include <stdio.h>
#include <stdlib.h>

#include "persona_logic.h"

static void expect_true(bool condition, const char* message) {
  if (!condition) {
    fprintf(stderr, "%s\n", message);
    exit(1);
  }
}

int main() {
  PersonaInputs input = {};

  expect_true(derivePersonaState(input) == P_SLEEP, "disconnected bridge should map to sleep");

  input.connected = true;
  expect_true(derivePersonaState(input) == P_IDLE, "connected with no activity should map to idle");

  input.sessionsRunning = 1;
  expect_true(derivePersonaState(input) == P_BUSY, "any actively running session should map to busy");

  input.sessionsWaiting = 1;
  expect_true(derivePersonaState(input) == P_ATTENTION, "approval pending should override busy");

  return 0;
}
