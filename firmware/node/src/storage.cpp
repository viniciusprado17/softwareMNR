#include "storage.h"

#include <Preferences.h>

static Preferences prefs;
static uint32_t seq = 0;

void storage_begin() {
  prefs.begin("coldchain", false);
  seq = prefs.getUInt("seq", 0);
}

uint32_t storage_last_seq() { return seq; }

uint32_t storage_next_seq() {
  seq++;
  prefs.putUInt("seq", seq);
  return seq;
}
