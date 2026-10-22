const clipList = document.querySelector("#clip-list");
const clipSearch = document.querySelector("#clip-search");
const utteranceSearch = document.querySelector("#utterance-search");
const utteranceList = document.querySelector("#utterance-list");
const utteranceCount = document.querySelector("#utterance-count");
const player = document.querySelector("#player");
const status = document.querySelector("#status");
const clipTitle = document.querySelector("#clip-title");
const speed = document.querySelector("#speed");
const speedValue = document.querySelector("#speed-value");
const captionsEnabled = document.querySelector("#captions-enabled");
const morphologyEnabled = document.querySelector("#morphology-enabled");
const morphologySetting = document.querySelector("#morphology-setting");
const caption = document.querySelector("#caption");
const morphologyPanel = document.querySelector("#morphology-panel");
const hideShort = document.querySelector("#hide-short");
const playPause = document.querySelector("#play-pause");
const progress = document.querySelector("#progress");
const audioTime = document.querySelector("#audio-time");
const speakerInfo = document.querySelector("#speaker-info");
const libraryCount = document.querySelector("#library-count");
const nextTrack = document.querySelector("#next-track");
const randomTrack = document.querySelector("#random-track");
const mainPanel = document.querySelector(".main-panel");
const themeToggle = document.querySelector("#theme-toggle");
const themeToggleLabel = document.querySelector("#theme-toggle-label");

const PREFERENCES_KEY = "seoul-corpus-tracker.preferences.v1";
let preferences = readPreferences();

let clips = [];
let currentClip = null;
let utterances = [];
let activeUtteranceEnd = null;
let activeUtterance = null;
let revealCandidate = null;
let revealedUtterance = null;
let selectionId = 0;
let estimatedDuration = 0;
let seeking = false;
let playbackIntent = false;
let playbackPending = false;
let playbackRequestId = 0;
let utteranceRequestId = 0;
let pendingUtteranceStart = null;
let posTags = {};
let highlightedMorpheme = null;

const utteranceCache = new Map();
const utteranceButtons = new Map();

function parseClipName(clipName) {
    const match = clipName.match(/^(s\d{2})([mf])(\d{2})([mf])([1-6])$/);
    if (!match) return null;
    const [, speakerId, speakerGender, speakerAge, interviewerGender, segment] = match;
    return {
        speaker_id: speakerId,
        speaker_gender: speakerGender === "m" ? "male" : "female",
        speaker_age: Number.parseInt(speakerAge, 10),
        interviewer_gender: interviewerGender === "m" ? "male" : "female",
        segment_number: Number.parseInt(segment, 10),
    };
}

function parseEntry(entry) {
    if (Array.isArray(entry)) {
        return {
            start: Number(entry[0]),
            end: Number(entry[1]),
            text: String(entry[2] ?? "").trim(),
            morphology: Array.isArray(entry[3]) ? entry[3] : [],
        };
    }
    return {
        start: Number(entry.start),
        end: Number(entry.end),
        text: String(entry.text ?? "").trim(),
        morphology: Array.isArray(entry.morphology) ? entry.morphology : [],
    };
}

function formatTime(seconds) {
    if (!Number.isFinite(seconds) || seconds < 0) return "--:--";
    const wholeSeconds = Math.floor(seconds);
    return `${Math.floor(wholeSeconds / 60)}:${String(wholeSeconds % 60).padStart(2, "0")}`;
}

async function getJson(url) {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`${response.status} ${response.statusText}`);
    return response.json();
}

function setStatus(message, state = "ready") {
    status.textContent = message;
    status.dataset.state = state;
}

function readPreferences() {
    try {
        const saved = JSON.parse(localStorage.getItem(PREFERENCES_KEY) || "{}");
        return saved && typeof saved === "object" && !Array.isArray(saved) ? saved : {};
    } catch {
        return {};
    }
}

function savePreference(key, value) {
    preferences[key] = value;
    try {
        localStorage.setItem(PREFERENCES_KEY, JSON.stringify(preferences));
    } catch {
        // Keep the current session usable when browser storage is unavailable.
    }
}

function applyTheme(theme, persist = false) {
    const selectedTheme = theme === "dark" ? "dark" : "light";
    const isDark = selectedTheme === "dark";
    document.documentElement.dataset.theme = selectedTheme;
    themeToggle.setAttribute("aria-pressed", String(isDark));
    themeToggle.setAttribute("aria-label", `Switch to ${isDark ? "light" : "dark"} theme`);
    themeToggleLabel.textContent = isDark ? "Light theme" : "Dark theme";
    if (persist) savePreference("theme", selectedTheme);
}

function restorePreferences() {
    const savedSpeed = Number(preferences.speed);
    const minimumSpeed = Number(speed.min);
    const maximumSpeed = Number(speed.max);
    if (Number.isFinite(savedSpeed) && savedSpeed >= minimumSpeed && savedSpeed <= maximumSpeed) {
        speed.value = String(savedSpeed);
    }

    captionsEnabled.checked = preferences.captionsEnabled === true;
    morphologyEnabled.checked = preferences.morphologyEnabled === true;
    updateMorphologyAvailability();
    hideShort.checked = preferences.hideShort !== false;
    const rate = Number(speed.value);
    speedValue.textContent = `${rate.toFixed(2)}×`;
    player.playbackRate = rate;
    applyTheme(preferences.theme);
    updateCaption(null);
}

function createEmptyState(title, message) {
    const state = document.createElement("div");
    state.className = "empty-state";
    const heading = document.createElement("strong");
    heading.textContent = title;
    const copy = document.createElement("span");
    copy.textContent = message;
    state.append(heading, copy);
    return state;
}

function renderClips() {
    const query = clipSearch.value.trim().toLowerCase();
    const visibleClips = clips.filter(name => name.toLowerCase().includes(query));
    clipList.replaceChildren();
    libraryCount.textContent = `${visibleClips.length} / ${clips.length}`;

    if (visibleClips.length === 0) {
        clipList.append(createEmptyState("No recordings found", "Try another speaker ID or segment."));
        return;
    }

    visibleClips.forEach(name => {
        const info = parseClipName(name);
        const button = document.createElement("button");
        button.type = "button";
        button.className = "clip-button";
        button.setAttribute("aria-current", name === currentClip ? "true" : "false");
        if (name === currentClip) button.classList.add("active");

        const index = document.createElement("span");
        index.className = "clip-index";
        index.textContent = info ? info.speaker_id.slice(1) : "—";

        const label = document.createElement("span");
        label.className = "clip-label";
        const clipName = document.createElement("span");
        clipName.className = "clip-name";
        clipName.textContent = name;
        const detail = document.createElement("span");
        detail.className = "clip-detail";
        detail.textContent = info
            ? `${info.speaker_age} years · segment ${info.segment_number}`
            : "Transcript recording";
        label.append(clipName, detail);

        const arrow = document.createElement("span");
        arrow.className = "clip-arrow";
        arrow.setAttribute("aria-hidden", "true");
        arrow.textContent = "›";
        button.append(index, label, arrow);
        button.addEventListener("click", () => selectClip(name));
        clipList.append(button);
    });
}

function resetAudioControls() {
    estimatedDuration = 0;
    seeking = false;
    progress.min = "0";
    progress.max = "0";
    progress.value = "0";
    progress.disabled = true;
    playPause.disabled = true;
    playPause.innerHTML = '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M5 3.5 12 8l-7 4.5z" fill="currentColor"/></svg><span>Play</span>';
    audioTime.textContent = "0:00 / 0:00";
}

function setEstimatedDuration() {
    progress.min = "0";
    progress.max = String(estimatedDuration);
    progress.value = "0";
    progress.disabled = estimatedDuration <= 0;
    playPause.disabled = !player.src;
    updateAudioControls();
}

function updateAudioControls() {
    const currentTime = Number.isFinite(player.currentTime) ? player.currentTime : 0;
    if (!seeking) progress.value = String(Math.min(currentTime, estimatedDuration));
    audioTime.textContent = `${formatTime(currentTime)} / ${formatTime(estimatedDuration)}`;
    const playing = playbackIntent || (!player.paused && !player.ended);
    playPause.setAttribute("aria-label", playing ? "Pause recording" : "Play recording");
    playPause.innerHTML = playing
        ? '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M4 3h3v10H4zm5 0h3v10H9z" fill="currentColor"/></svg><span>Pause</span>'
        : '<svg viewBox="0 0 16 16" aria-hidden="true"><path d="M5 3.5 12 8l-7 4.5z" fill="currentColor"/></svg><span>Play</span>';
    playPause.dataset.pending = String(playbackPending);
}

function finishPlaybackRequest(error, requestId) {
    if (requestId !== playbackRequestId || !playbackIntent) return;
    playbackIntent = false;
    playbackPending = false;
    updateAudioControls();

    // A pending play request is expected to reject if a rapid pause cancels it.
    if (error?.name !== "AbortError") {
        setStatus(`Playback failed: ${error.message}`, "error");
    }
}

function requestPlayback(shouldPlay) {
    playbackIntent = shouldPlay;
    playbackPending = shouldPlay;
    const requestId = ++playbackRequestId;

    if (!shouldPlay) {
        player.pause();
        updateAudioControls();
        return;
    }

    if (estimatedDuration > 0 && player.currentTime >= estimatedDuration) {
        player.currentTime = 0;
    }
    updateAudioControls();

    try {
        const playRequest = player.play();
        if (playRequest && typeof playRequest.catch === "function") {
            playRequest.catch(error => finishPlaybackRequest(error, requestId));
        }
    } catch (error) {
        finishPlaybackRequest(error, requestId);
    }
}

function cancelPendingUtteranceStart() {
    if (!pendingUtteranceStart) return;
    player.removeEventListener("loadedmetadata", pendingUtteranceStart);
    pendingUtteranceStart = null;
}

function renderSpeakerInfo(name) {
    speakerInfo.replaceChildren();
    const info = parseClipName(name);
    if (!info) {
        speakerInfo.hidden = true;
        return;
    }
    speakerInfo.hidden = false;
    const fields = [
        ["age", "Age", `${info.speaker_age} years`],
        ["gender", "Gender", info.speaker_gender],
        ["interviewer", "Interviewer", info.interviewer_gender],
        ["segment", "Segment", String(info.segment_number)],
    ];
    fields.forEach(([kind, label, value]) => {
        const chip = document.createElement("span");
        chip.className = `meta-chip ${kind}`;
        const name = document.createElement("strong");
        name.textContent = `${label}:`;
        const text = document.createElement("span");
        text.textContent = value;
        chip.append(name, text);
        speakerInfo.append(chip);
    });
}

async function selectClip(name) {
    const thisSelection = ++selectionId;
    utteranceRequestId += 1;
    cancelPendingUtteranceStart();
    currentClip = name;
    savePreference("selectedClip", name);
    mainPanel.classList.add("has-selection");
    utterances = [];
    activeUtterance = null;
    activeUtteranceEnd = null;
    revealCandidate = null;
    revealedUtterance = null;
    utteranceButtons.clear();
    utteranceList.scrollTop = 0;
    utteranceList.scrollLeft = 0;

    requestPlayback(false);
    player.removeAttribute("src");
    player.load();
    resetAudioControls();
    caption.textContent = captionsEnabled.checked ? "" : "Captions are off";
    caption.classList.toggle("disabled", !captionsEnabled.checked);
    renderClips();
    clipTitle.textContent = name;
    renderSpeakerInfo(name);
    utteranceList.replaceChildren();
    utteranceCount.textContent = "";
    utteranceSearch.value = "";
    setStatus(`Opening ${name}…`);

    try {
        if (!utteranceCache.has(name)) {
            const data = await getJson(`transcripts_json/${encodeURIComponent(name)}.json`);
            utteranceCache.set(name, {
                utterances: (data.utterances || []).map(parseEntry),
                length: Number(data.length) || 0,
            });
        }
        if (thisSelection !== selectionId) return;

        const cached = utteranceCache.get(name);
        utterances = cached.utterances;
        estimatedDuration = cached.length;
        renderUtterances();
        setEstimatedDuration();
        player.src = `/api/clips/${encodeURIComponent(name)}/play`;
        player.playbackRate = Number(speed.value);
        player.load();
        playPause.disabled = estimatedDuration <= 0;
        setStatus(`${utterances.length} utterances loaded · select a line to listen closely`);
    } catch (error) {
        if (thisSelection !== selectionId) return;
        utteranceList.replaceChildren(createEmptyState("Transcript unavailable", "Try choosing this recording again in a moment."));
        setStatus(`Could not load recording: ${error.message}`, "error");
    }
}

function getVisibleUtterances() {
    const query = utteranceSearch.value.trim().toLowerCase();
    return utterances.filter(item => {
        const matchesSearch = item.text.toLowerCase().includes(query);
        const characterCount = item.text.replace(/\s/g, "").length;
        return matchesSearch && !(hideShort.checked && characterCount <= 3);
    });
}

function utterancePlayLabel(item, textHidden) {
    return textHidden
        ? `Play utterance at ${formatTime(item.start)}. Text is hidden.`
        : `Play utterance at ${formatTime(item.start)}: ${item.text}`;
}

function utteranceTextNeedsExpansion(row, button, text, baselineWidth) {
    if (!text.textContent) return false;

    const range = document.createRange();
    range.selectNodeContents(text);
    const textWidth = range.getBoundingClientRect().width;
    const rowStyle = window.getComputedStyle(row);
    const buttonStyle = window.getComputedStyle(button);
    const controlWidth = Number.parseFloat(rowStyle.getPropertyValue("--reveal-control-width")) || 0;
    const controlGap = Number.parseFloat(rowStyle.getPropertyValue("--reveal-control-gap")) || 0;
    const timestampWidth = Number.parseFloat(buttonStyle.gridTemplateColumns) || 0;
    const innerGap = Number.parseFloat(buttonStyle.columnGap) || 0;
    const buttonPaddingAndBorder = [
        "paddingLeft",
        "paddingRight",
        "borderLeftWidth",
        "borderRightWidth"
    ].reduce((total, property) => total + (Number.parseFloat(buttonStyle[property]) || 0), 0);
    const availableTextWidth =
        baselineWidth -
        controlWidth -
        controlGap -
        timestampWidth -
        innerGap -
        buttonPaddingAndBorder;

    return textWidth > availableTextWidth + 1;
}

function clearUtteranceTextAfterResize(row, text, item) {
    let fallbackTimer;
    const finish = () => {
        if (revealedUtterance !== item) text.textContent = "";
        row.removeEventListener("transitionend", onTransitionEnd);
        window.clearTimeout(fallbackTimer);
    };
    const onTransitionEnd = event => {
        if (event.target === row && event.propertyName === "width") finish();
    };

    row.addEventListener("transitionend", onTransitionEnd);
    fallbackTimer = window.setTimeout(finish, 350);
}

function syncUtteranceReveal(item) {
    const button = utteranceButtons.get(item);
    if (!button) return;

    const row = button.parentElement;
    const text = button.querySelector(".utterance-text");
    const textHidden = !captionsEnabled.checked && revealedUtterance !== item;
    const shouldShowReveal = !captionsEnabled.checked && revealCandidate === item;
    const wasExpanded = row.classList.contains("is-revealed");
    const otherRowWidths = [...utteranceList.querySelectorAll(".utterance-row")]
        .filter(otherRow => otherRow !== row)
        .map(otherRow => otherRow.getBoundingClientRect().width);
    const listStyle = window.getComputedStyle(utteranceList);
    const baselineWidth = otherRowWidths.length
        ? Math.max(...otherRowWidths)
        : utteranceList.clientWidth -
            (Number.parseFloat(listStyle.paddingLeft) || 0) -
            (Number.parseFloat(listStyle.paddingRight) || 0);
    const deferHidingText =
        textHidden &&
        text.textContent.length > 0 &&
        row.getBoundingClientRect().width > baselineWidth + 1 &&
        CSS.supports("interpolate-size: allow-keywords") &&
        !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    if (!deferHidingText) text.textContent = textHidden ? "" : item.text;
    button.setAttribute("aria-label", utterancePlayLabel(item, textHidden));
    row.classList.toggle("has-reveal", shouldShowReveal);
    const shouldExpand =
        shouldShowReveal &&
        revealedUtterance === item &&
        (wasExpanded || utteranceTextNeedsExpansion(row, button, text, baselineWidth));
    row.classList.toggle("is-revealed", shouldExpand);
    if (deferHidingText) clearUtteranceTextAfterResize(row, text, item);

    let revealButton = row.querySelector(".reveal-text-button");
    if (!shouldShowReveal) {
        revealButton?.remove();
        return;
    }

    if (!revealButton) {
        revealButton = document.createElement("button");
        revealButton.type = "button";
        revealButton.className = "reveal-text-button";
        revealButton.addEventListener("click", () => {
            const shouldReveal = revealedUtterance !== item;
            revealedUtterance = shouldReveal ? item : null;
            syncUtteranceReveal(item);
        });
        row.append(revealButton);
    }

    revealButton.textContent = revealedUtterance === item ? "Hide text" : "Reveal text";
    revealButton.setAttribute(
        "aria-label",
        revealedUtterance === item ? "Hide this utterance's text" : "Reveal this utterance's text"
    );
}

function renderUtterances() {
    const filtered = getVisibleUtterances();
    utteranceList.classList.toggle("captions-hidden", !captionsEnabled.checked);
    utteranceList.replaceChildren();
    utteranceButtons.clear();
    utteranceCount.textContent = `${filtered.length} shown / ${utterances.length} total utterances`;

    if (!filtered.length) {
        const isFiltering = utteranceSearch.value.trim() || hideShort.checked;
        utteranceList.append(createEmptyState(
            isFiltering ? "No lines match" : "Transcript is ready",
            isFiltering ? "Adjust the text search or short-line filter." : "Utterances will appear here."
        ));
        return;
    }

    filtered.forEach(item => {
        const row = document.createElement("div");
        row.className = "utterance-row";

        const button = document.createElement("button");
        button.type = "button";
        button.className = "utterance";
        const textHidden = !captionsEnabled.checked && revealedUtterance !== item;
        button.setAttribute("aria-label", utterancePlayLabel(item, textHidden));
        const time = document.createElement("span");
        time.className = "timestamp";
        time.textContent = `${formatTime(item.start)} – ${formatTime(item.end)}`;
        const text = document.createElement("span");
        text.className = "utterance-text";
        text.lang = "ko";
        text.textContent = textHidden ? "" : item.text;
        button.append(time, text);
        utteranceButtons.set(item, button);
        if (activeUtterance === item) button.classList.add("active");
        button.addEventListener("click", () => playUtterance(item));
        row.append(button);
        utteranceList.append(row);
        syncUtteranceReveal(item);
    });
}

async function playUtterance(item) {
    const thisSelection = selectionId;
    const thisUtteranceRequest = ++utteranceRequestId;
    cancelPendingUtteranceStart();
    const previousRevealCandidate = revealCandidate;
    if (captionsEnabled.checked) {
        revealCandidate = null;
        revealedUtterance = null;
    } else if (revealCandidate !== item) {
        revealCandidate = item;
        revealedUtterance = null;
    }
    activeUtterance = item;
    activeUtteranceEnd = item.end;
    if (previousRevealCandidate && previousRevealCandidate !== revealCandidate) {
        syncUtteranceReveal(previousRevealCandidate);
    }
    if (revealCandidate) syncUtteranceReveal(revealCandidate);
    utteranceButtons.forEach((button, utterance) => {
        button.classList.toggle("active", utterance === item);
    });
    const button = utteranceButtons.get(item);
    if (button) {
        button.focus({ preventScroll: true });
        scrollActiveUtteranceIntoView(button);
    }
    updateCaption(item);

    const seekAndPlay = async () => {
        if (pendingUtteranceStart === seekAndPlay) {
            pendingUtteranceStart = null;
        }
        if (
            thisSelection !== selectionId ||
            thisUtteranceRequest !== utteranceRequestId
        ) return;
        try {
            player.currentTime = item.start;
            requestPlayback(true);
        } catch (error) {
            activeUtteranceEnd = null;
            setStatus(`Playback failed: ${error.message}`, "error");
        }
    };

    if (player.readyState >= 1) {
        await seekAndPlay();
    } else {
        pendingUtteranceStart = seekAndPlay;
        player.addEventListener("loadedmetadata", seekAndPlay, { once: true });
    }
}

function updateMorphologyAvailability() {
    const captionsVisible = captionsEnabled.checked;
    morphologyEnabled.disabled = !captionsVisible;
    morphologySetting.classList.toggle("is-disabled", !captionsVisible);
    if (!captionsVisible) morphologyEnabled.checked = false;
}

function renderMorphology(item) {
    morphologyPanel.replaceChildren();
    const shouldShow = captionsEnabled.checked && morphologyEnabled.checked && item;
    morphologyPanel.hidden = !shouldShow;
    highlightedMorpheme = null;
    if (!shouldShow) return;

    const label = document.createElement("span");
    label.className = "morphology-label";
    label.textContent = "Morpheme map · tap a chip to explore";
    const tokens = document.createElement("div");
    tokens.className = "morpheme-tokens";
    item.morphology.forEach(([form, tag], index) => {
        const info = posTags[String(tag)] || {};
        const token = document.createElement("button");
        token.type = "button";
        token.className = "morpheme-token";
        token.dataset.tag = String(tag);
        token.style.setProperty("--morpheme-color", morphemeColor(String(tag)));
        token.setAttribute("aria-label", `${form}, ${info.english || tag}`);
        const formNode = document.createElement("b");
        formNode.textContent = String(form);
        const popup = document.createElement("span");
        popup.className = "morpheme-info";
        popup.setAttribute("role", "tooltip");
        popup.innerHTML = `<strong>${escapeHtml(info.name || String(tag))}</strong><em>${escapeHtml(info.english || "Part of speech")}</em><span>${escapeHtml(info.meaning || "No description available.")}</span>${info.example ? `<small>Example: ${escapeHtml(info.example)}</small>` : ""}`;
        token.append(formNode, popup);
        const activate = event => {
            event.stopPropagation();
            highlightedMorpheme = highlightedMorpheme === index ? null : index;
            renderCaptionText(item);
            tokens.querySelectorAll(".morpheme-token").forEach((other, otherIndex) => other.classList.toggle("is-selected", otherIndex === highlightedMorpheme));
        };
        token.addEventListener("mouseenter", () => { highlightedMorpheme = index; renderCaptionText(item); });
        token.addEventListener("mouseleave", () => { highlightedMorpheme = null; renderCaptionText(item); });
        token.addEventListener("focus", () => { highlightedMorpheme = index; renderCaptionText(item); });
        token.addEventListener("blur", () => { highlightedMorpheme = null; renderCaptionText(item); });
        token.addEventListener("click", activate);
        tokens.append(token);
    });
    morphologyPanel.append(label, tokens);
}

const MORPHEME_COLORS = [
    "#c2415d", "#2563a8", "#0f766e", "#9a6700", "#7c3aed",
    "#b45309", "#047857", "#be185d", "#4338ca", "#15803d",
    "#c026d3", "#0369a1", "#a16207", "#6d28d9", "#0f766e"
];

function morphemeColor(tag) {
    const hash = [...tag].reduce((total, character) => total * 31 + character.charCodeAt(0), 0);
    return MORPHEME_COLORS[Math.abs(hash) % MORPHEME_COLORS.length];
}

function renderCaptionText(item) {
    caption.replaceChildren();
    if (!item) return;
    const text = item.text;
    let cursor = 0;
    item.morphology.forEach(([form], index) => {
        const value = String(form);
        const matchValue = value.trim();
        const start = matchValue ? text.indexOf(matchValue, cursor) : -1;
        if (start < 0) return;
        caption.append(document.createTextNode(text.slice(cursor, start)));
        const span = document.createElement("span");
        span.className = "caption-morpheme";
        span.textContent = matchValue;
        span.classList.toggle("is-highlighted", index === highlightedMorpheme);
        span.style.setProperty("--morpheme-color", morphemeColor(String(item.morphology[index][1])));
        caption.append(span);
        cursor = start + matchValue.length;
    });
    caption.append(document.createTextNode(text.slice(cursor)));
}

function escapeHtml(value) {
    return value.replace(/[&<>'"]/g, character => ({
        "&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&#39;", "\"": "&quot;"
    }[character]));
}

function updateCaption(item) {
    if (!captionsEnabled.checked) {
        caption.textContent = "Captions are off";
        caption.classList.add("disabled");
        morphologyPanel.hidden = true;
        return;
    }
    caption.classList.remove("disabled");
    renderCaptionText(item);
    renderMorphology(item);
}

function scrollActiveUtteranceIntoView(button) {
    const listBounds = utteranceList.getBoundingClientRect();
    const buttonBounds = button.getBoundingClientRect();
    const inset = 6;
    let scrollDelta = 0;

    if (buttonBounds.top < listBounds.top + inset) {
        scrollDelta = buttonBounds.top - listBounds.top - inset;
    } else if (buttonBounds.bottom > listBounds.bottom - inset) {
        scrollDelta = buttonBounds.bottom - listBounds.bottom + inset;
    }

    if (scrollDelta) {
        utteranceList.scrollBy({ top: scrollDelta, behavior: "smooth" });
    }
}

function updateActiveUtterance(time) {
    let current = null;
    for (const item of utterances) {
        if (item.start <= time) {
            if (current === null || item.start >= current.start) current = item;
        } else {
            break;
        }
    }
    if (current !== activeUtterance) {
        activeUtterance = current;
        utteranceButtons.forEach(button => button.classList.remove("active"));
        const button = current ? utteranceButtons.get(current) : null;
        if (button) {
            button.classList.add("active");
            scrollActiveUtteranceIntoView(button);
        }
        updateCaption(current);
    }
}

function chooseNextTrack(random = false) {
    if (!clips.length) return;
    if (random) {
        const choices = clips.filter(name => name !== currentClip);
        const pool = choices.length ? choices : clips;
        selectClip(pool[Math.floor(Math.random() * pool.length)]);
        return;
    }
    const index = clips.indexOf(currentClip);
    selectClip(clips[index < 0 ? 0 : (index + 1) % clips.length]);
}

playPause.addEventListener("click", () => {
    if (!player.src) return;
    const shouldPlay = !playbackIntent && (player.paused || player.ended);
    if (shouldPlay && activeUtteranceEnd === null && revealCandidate !== null) {
        const previousRevealCandidate = revealCandidate;
        revealCandidate = null;
        revealedUtterance = null;
        syncUtteranceReveal(previousRevealCandidate);
    }
    requestPlayback(shouldPlay);
});

themeToggle.addEventListener("click", () => {
    const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    applyTheme(nextTheme, true);
});

progress.addEventListener("input", () => {
    seeking = true;
    audioTime.textContent = `${formatTime(Number(progress.value))} / ${formatTime(estimatedDuration)}`;
});

progress.addEventListener("change", () => {
    const targetTime = Number(progress.value);
    seeking = false;
    if (Number.isFinite(targetTime)) {
        if (
            revealCandidate &&
            (targetTime < revealCandidate.start || targetTime >= revealCandidate.end)
        ) {
            const previousRevealCandidate = revealCandidate;
            revealCandidate = null;
            revealedUtterance = null;
            syncUtteranceReveal(previousRevealCandidate);
        }
        player.currentTime = targetTime;
        updateActiveUtterance(targetTime);
    }
    updateAudioControls();
});

speed.addEventListener("input", () => {
    const rate = Number(speed.value);
    player.playbackRate = rate;
    speedValue.textContent = `${rate.toFixed(2)}×`;
    savePreference("speed", rate);
});

captionsEnabled.addEventListener("change", () => {
    savePreference("captionsEnabled", captionsEnabled.checked);
    updateMorphologyAvailability();
    revealCandidate = null;
    revealedUtterance = null;
    updateCaption(activeUtterance);
    renderUtterances();
});
morphologyEnabled.addEventListener("change", () => {
    savePreference("morphologyEnabled", morphologyEnabled.checked);
    renderMorphology(activeUtterance);
});
hideShort.addEventListener("change", () => {
    savePreference("hideShort", hideShort.checked);
    renderUtterances();
});
clipSearch.addEventListener("input", renderClips);
utteranceSearch.addEventListener("input", renderUtterances);
nextTrack.addEventListener("click", () => chooseNextTrack());
randomTrack.addEventListener("click", () => chooseNextTrack(true));

player.addEventListener("timeupdate", () => {
    const time = player.currentTime;
    if (activeUtteranceEnd !== null && time >= activeUtteranceEnd) {
        const end = activeUtteranceEnd;
        activeUtteranceEnd = null;
        requestPlayback(false);
        player.currentTime = end;
        updateCaption(activeUtterance);
        updateAudioControls();
        return;
    }
    updateActiveUtterance(time);
    updateAudioControls();
});

player.addEventListener("play", updateAudioControls);
player.addEventListener("playing", () => {
    playbackPending = false;
    updateAudioControls();
});
player.addEventListener("pause", updateAudioControls);
player.addEventListener("ended", () => {
    activeUtteranceEnd = null;
    playbackIntent = false;
    playbackPending = false;
    updateAudioControls();
});
player.addEventListener("error", () => {
    playbackRequestId += 1;
    playbackIntent = false;
    playbackPending = false;
    updateAudioControls();
    if (currentClip) setStatus("Audio failed to load. Check the playback endpoint.", "error");
});

async function init() {
    try {
        const [data, tagData] = await Promise.all([getJson("clips.json"), getJson("pos_tags.json")]);
        posTags = tagData.tags || {};
        clips = data
            .filter(name => typeof name === "string")
            .map(name => name.replace(/\.json$/, ""))
            .sort();
        nextTrack.disabled = clips.length === 0;
        randomTrack.disabled = clips.length === 0;
        renderClips();
        if (typeof preferences.selectedClip === "string" && clips.includes(preferences.selectedClip)) {
            await selectClip(preferences.selectedClip);
            return;
        }
        setStatus(`${clips.length} recordings ready · choose a voice to begin`);
    } catch (error) {
        nextTrack.disabled = true;
        randomTrack.disabled = true;
        renderClips();
        clipList.replaceChildren(createEmptyState("Library unavailable", "Reload the page to try again."));
        setStatus(`Could not load recordings: ${error.message}`, "error");
    }
}

restorePreferences();
init();