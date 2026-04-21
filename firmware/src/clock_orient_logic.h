#pragma once

#include <math.h>
#include <stdint.h>

inline void clockOrientUpdateForStickS3(
  uint8_t* clock_orient,
  int8_t* orient_frames,
  int8_t* swap_frames,
  float ax,
  float ay,
  float az,
  uint8_t lock
) {
  const float primary = ay;
  const float secondary = ax;

  if (lock == 1) {
    *clock_orient = 0;
    return;
  }

  if (lock == 2) {
    if (*clock_orient == 0) *clock_orient = (primary >= 0) ? 1 : 3;
    if      (primary >  0.5f && *clock_orient != 1) *clock_orient = 1;
    else if (primary < -0.5f && *clock_orient != 3) *clock_orient = 3;
    return;
  }

  bool side = (*clock_orient == 0)
    ? fabsf(primary) > 0.7f && fabsf(secondary) < 0.5f && fabsf(az) < 0.5f
    : fabsf(primary) > 0.4f;

  if (side) {
    if (*orient_frames < 20) (*orient_frames)++;
  } else {
    if (*orient_frames > -10) (*orient_frames)--;
  }

  if (*clock_orient == 0 && *orient_frames >= 15) {
    *clock_orient = (primary > 0) ? 1 : 3;
  } else if (*clock_orient != 0 && *orient_frames <= -8) {
    *clock_orient = 0;
  } else if (*clock_orient != 0 && side) {
    uint8_t want = (primary > 0) ? 1 : 3;
    if (want != *clock_orient) {
      if (++(*swap_frames) >= 8) {
        *clock_orient = want;
        *swap_frames = 0;
      }
    } else {
      *swap_frames = 0;
    }
  }
}
