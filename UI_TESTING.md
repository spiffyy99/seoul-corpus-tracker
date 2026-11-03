# Regression Test Plan

This document lists UI and functional regression tests for the K-Corpus Listener. It is derived from bugs that have actually shipped in the past — each test exists to catch a specific regression.

## History (bugs that motivated these tests)

| Bug | Test IDs |
|-----|----------|
| Pause mid-utterance → play seeks to utterance end | P2, P3 |
| Play after natural end pauses immediately (needs second press) | P5 |
| Seeker frozen after utterance ends | P7 |
| Play after natural end → pause → play jumps back to utterance end | P6 |
| `createBuffer` throws on 0-frame segments | P8 |
| `hideShort` checkbox state persists across modes (shared flag) | S1, S2, S3 |
| Screen snapping when switching modes with active item | M1, M2, M3 |
| Active item not centered after filter toggle | M4, M5, M6 |
| Words feel cut off (tight timestamps) | A2, A5 |
| Pitch changes with speed (should be preserved) | A6, A7 |
| Repeated playback hits network instead of cache | A8, A10 |
| Cache lost on page restart | A9, A11 |
| Reveal state resets on search/filter/mode toggle | S7 |
| Translation popup re-translates duplicate text | S8 |
| Morphology HTML leaks into translation | S9 |

## Framework

**Playwright** (already in use via MCP). Zero new dependencies.

```bash
npm install --save-dev @playwright/test
```

One `playwright.config.ts` with:

```js
export default defineConfig({
  webServer: { command: 'python local.py', port: 3000, timeout: 15000 },
});
```

## Test Structure

Plain JS, one spec file per concern. No Page Object Model needed at this scale.

```
tests/
  playback.spec.js   # playback control (P1-P10)
  scroll.spec.js     # mode switching & scrolling (M1-M6)
  preferences.spec.js # state & preferences (S1-S6)
  audio.spec.js      # audio accuracy (A1-A4)
```

## Test Cases

### 1. Playback Control

| ID  | Test | Assert |
|-----|------|--------|
| P1  | Click utterance → play | `#play-pause` label = "Pause", `player.currentTime` > 0 |
| P2  | Pause mid-utterance | `player.currentTime` stays at pause point (not jumped to utterance end) |
| P3  | Play again after mid-utterance pause | Resumes from pause point, not from 0 or utterance end |
| P4  | Let utterance end naturally | Label flips to "Play", `activeUtteranceEnd` is null |
| P5  | Play after natural end | First press plays; label becomes "Pause" immediately |
| P6  | Pause then play again (post-natural-end) | Continues forward from pause point |
| P7  | Seeker/progress bar | `#progress.value` advances during resumed blob playback |
| P8  | createBuffer 0 frames | Clicking edge-case word doesn't throw; playback starts |
| P9  | Speed change mid-playback | `player.playbackRate` updates |
| P10 | Volume change | `player.volume` updates |

### 2. Mode Switching & Scrolling

| ID  | Test | Assert |
|-----|------|--------|
| M1  | Switch utterance→word with active utterance | Active word highlighted; no page scroll |
| M2  | Switch word→utterance with active word | Active utterance highlighted; no page scroll |
| M3  | Active item centered after mode switch | Active row vertically centered in `#utterance-list` |
| M4  | Active item centered after filter toggle | Active row still centered (if visible) |
| M5  | Filter removes active item | No scroll attempt; list shows filtered results |
| M6  | Filter doesn't change list | No scroll at all |

### 3. Preferences & State

| ID  | Test | Assert |
|-----|------|--------|
| S1  | Toggle hide-short in utterance mode | Persists after switching to word mode |
| S2  | Toggle hide-short in word mode | Independent from utterance-mode setting |
| S3  | Switch modes and back | Each mode restores its own hide-short setting |
| S4  | Captions toggle | Caption text shows/hides |
| S5  | Morphology toggle | Morphology cards appear/disappear |
| S6  | localStorage persistence | Reload page → preferences restored |
| S7  | Reveal state resets on search/filter/mode toggle | Re-tapping a word shows "Reveal text"; previously hidden text re-hides on re-render |
| S8  | Translation popup doesn't re-translate duplicate text | Clicking same morpheme twice doesn't trigger duplicate translation |
| S9  | Morphology HTML stripped before translation | `<...>` tags in morphology don't leak into translated popup text |
| S10 | IndexedDB translation cache | Re-opening same morpheme popup serves cached translation (no duplicate fetch) |

### 4. Audio Accuracy

| ID  | Test | Assert |
|-----|------|--------|
| A1  | Utterance boundaries | `playSegment` called with exact `item.start`/`item.end` |
| A2  | Word boundaries | Word `end` = `span[1] + 0.1` |
| A3  | SoundTouch for segments | `AudioContext.createBufferSource` used (not HTML5 `<audio>`) |
| A4  | Blob playback uses `<audio>` | `requestPlayback` calls `player.play()` |
| A5  | Word start/end times are accurate | `playSegment` is called with the exact `item.start`/`item.end` from the transcript (spy on `playSegment` or assert `activeUtteranceEnd === item.end + WORD_END_PADDING`) |
| A6  | Pitch preserved at non-1× speed | Changing `#speed` calls `SoundTouch` with `st.tempo = rate` (not `player.playbackRate`); HTML5 `<audio>` is only used for blob playback |
| A7  | Speed change doesn't switch playback engine | Changing `#speed` mid-segment keeps `bufferPlaying = true` (SoundTouch path), doesn't fall back to `<audio>.playbackRate` |
| A8  | Blob playback cached in IndexedDB | Second play of same clip → no network request to `/api/clips/{name}/play`; `idbGetAudio` returns cached blob |
| A9  | Blob cache survives page restart | Reload page → re-selecting same clip → no network request; cached blob served from IndexedDB |
| A10 | `/api/clips/{name}/play` not called when cached | Spy on `fetch`/network: after first play, subsequent plays of same clip produce zero requests to `/play` |
| A11 | `/play` not called after page restart | Reload → select same clip → zero `/play` requests (served entirely from IndexedDB) |

### 5. Data & Loading

| ID  | Test | Assert |
|-----|------|--------|
| D1  | Clip selection | `#status` shows utterance count; `#clip-title` updates |
| D2  | Empty state | No clip selected → empty state shown |
| D3  | Search filters | Typing in `#utterance-search` reduces visible rows |
| D4  | Clip search | Typing in `#clip-search` filters clip list |
| D5  | Network error | Graceful error message; no console crash |

## Implementation Patterns

- **Direct DOM assertions** — read `player.currentTime`, `#progress.value`, element classes.
- **State via data attributes** — `playPause.dataset.pending`, `#status.dataset.state`.
- **One spec file per concern** — failures isolated.
- **CI hook** — `npm test` runs `playwright test` on every push to `dist/app.js` or `dist/styles.css`.
- **No audio in CI** — assert on state transitions (`playbackIntent`, `bufferPlaying`, `activeUtteranceEnd`, `player.currentTime`), not actual audio output.

## What to Avoid

- Don't test exact `currentTime` values (timing-dependent). Test relative behavior.
- Don't test SoundTouch internals. Test the observable contract.
- Don't test the full utterance→end→play→pause→play cycle in one test. Break into P2/P3/P5/P6.