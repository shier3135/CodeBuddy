#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#include "clock_orient_logic.h"

static void expect_true(bool condition, const char* message) {
  if (!condition) {
    fprintf(stderr, "%s\n", message);
    exit(1);
  }
}

int main() {
  uint8_t orient = 0;
  int8_t frames = 0;
  int8_t swap_frames = 0;

  for (int i = 0; i < 16; ++i) {
    clockOrientUpdateForStickS3(&orient, &frames, &swap_frames, 0.95f, 0.0f, 0.0f, 0);
  }
  expect_true(orient == 0, "x-dominant portrait hold should stay portrait on StickS3");

  orient = 0;
  frames = 0;
  swap_frames = 0;
  for (int i = 0; i < 16; ++i) {
    clockOrientUpdateForStickS3(&orient, &frames, &swap_frames, 0.0f, 0.95f, 0.0f, 0);
  }
  expect_true(orient != 0, "y-dominant sideways hold should enter landscape on StickS3");

  return 0;
}
