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
const caption = document.querySelector("#caption");
const hideShort = document.querySelector("#hide-short");
const playPause = document.querySelector("#play-pause");
const progress = document.querySelector("#progress");
const audioTime = document.querySelector("#audio-time");
const speakerInfo = document.querySelector("#speaker-info");
const libraryCount = document.querySelector("#library-count");
const nextTrack = document.querySelector("#next-track");
const randomTrack = document.querySelector("#random-track");

let clips = [];
let currentClip = null;
let utterances = [];
let activeUtteranceEnd = null;
let activeUtterance = null;
let selectionId = 0;
let estimatedDuration = 0;
let seeking = false;
let playbackIntent = false;
let playbackPending = false;
let playbackRequestId = 0;
let utteranceRequestId = 0;
let pendingUtteranceStart = null;

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
        return { start: Number(entry[0]), end: Number(entry[1]), text: String(entry[2] ?? "").trim() };
    }
    return { start: Number(entry.start), end: Number(entry.end), text: String(entry.text ?? "").trim() };
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
    utterances = [];
    activeUtterance = null;
    activeUtteranceEnd = null;
    utteranceButtons.clear();

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

function renderUtterances() {
    const filtered = getVisibleUtterances();
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
        const button = document.createElement("button");
        button.type = "button";
        button.className = "utterance";
        button.setAttribute("aria-label", `Play utterance at ${formatTime(item.start)}: ${item.text}`);
        const time = document.createElement("span");
        time.className = "timestamp";
        time.textContent = `${formatTime(item.start)} – ${formatTime(item.end)}`;
        const text = document.createElement("span");
        text.className = "utterance-text";
        text.lang = "ko";
        text.textContent = item.text;
        button.append(time, text);
        utteranceButtons.set(item, button);
        if (activeUtterance === item) button.classList.add("active");
        button.addEventListener("click", () => playUtterance(item));
        utteranceList.append(button);
    });
}

async function playUtterance(item) {
    const thisSelection = selectionId;
    const thisUtteranceRequest = ++utteranceRequestId;
    cancelPendingUtteranceStart();
    activeUtterance = item;
    activeUtteranceEnd = item.end;
    utteranceButtons.forEach(button => button.classList.remove("active"));
    const button = utteranceButtons.get(item);
    if (button) button.classList.add("active");
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

function updateCaption(item) {
    if (!captionsEnabled.checked) {
        caption.textContent = "Captions are off";
        caption.classList.add("disabled");
        return;
    }
    caption.classList.remove("disabled");
    caption.textContent = item ? item.text : "";
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
        if (button) button.classList.add("active");
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
    requestPlayback(!playbackIntent && (player.paused || player.ended));
});

progress.addEventListener("input", () => {
    seeking = true;
    audioTime.textContent = `${formatTime(Number(progress.value))} / ${formatTime(estimatedDuration)}`;
});

progress.addEventListener("change", () => {
    const targetTime = Number(progress.value);
    seeking = false;
    if (Number.isFinite(targetTime)) {
        player.currentTime = targetTime;
        updateActiveUtterance(targetTime);
    }
    updateAudioControls();
});

speed.addEventListener("input", () => {
    const rate = Number(speed.value);
    player.playbackRate = rate;
    speedValue.textContent = `${rate.toFixed(2)}×`;
});

captionsEnabled.addEventListener("change", () => updateCaption(activeUtterance));
hideShort.addEventListener("change", renderUtterances);
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
        const data = await getJson("clips.json");
        clips = data
            .filter(name => typeof name === "string")
            .map(name => name.replace(/\.json$/, ""))
            .sort();
        nextTrack.disabled = clips.length === 0;
        randomTrack.disabled = clips.length === 0;
        renderClips();
        setStatus(`${clips.length} recordings ready · choose a voice to begin`);
    } catch (error) {
        nextTrack.disabled = true;
        randomTrack.disabled = true;
        renderClips();
        clipList.replaceChildren(createEmptyState("Library unavailable", "Reload the page to try again."));
        setStatus(`Could not load recordings: ${error.message}`, "error");
    }
}

init();
