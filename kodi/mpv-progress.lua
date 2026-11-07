-- kodi-mpv progress reporter (see ../userdata.nix and moviepipe/progress.py).
--
-- mpv has no idea about kodi's library: this writes one small JSON file per
-- mpv process into $KODI_MPV_STATE, and moviepipe's service maps the path to
-- a kodi file id, then writes lastPlayed, the resume bookmark and the watched
-- flag into kodi's video database. The skin's progress bars and the "in
-- progress" lists are plain kodi data, so they start working with it.
--
-- Written on file load, every second while playing, and on end/shutdown.
-- Atomic rename, so the service never reads a half file.
local json = {}

local function escape(value)
    value = value:gsub("\\", "\\\\")
    value = value:gsub('"', '\\"')
    value = value:gsub("\n", "\\n")
    value = value:gsub("\r", "\\r")
    value = value:gsub("\t", "\\t")
    return value
end

local state_dir = os.getenv("KODI_MPV_STATE")
if not state_dir or state_dir == "" then
    state_dir = "/tmp/kodi-mpv"
end

local pid = tostring(mp.get_property_native("pid") or 0)
local started = os.time()
local ended = false

local function write_state()
    local path = mp.get_property_native("path")
    if not path or path == "" then
        return
    end
    local position = mp.get_property_number("time-pos") or 0
    local duration = mp.get_property_number("duration") or 0
    local paused = mp.get_property_bool("pause") or false
    local eof = mp.get_property_bool("eof-reached") or false
    if eof then
        ended = true
        if duration > 0 then
            position = duration
        end
    end

    local payload = string.format(
        '{"path":"%s","position":%.3f,"duration":%.3f,"paused":%s,"ended":%s,"started":%d,"updated":%d,"pid":%s}',
        escape(path), position, duration, tostring(paused), tostring(ended or eof),
        started, os.time(), pid)

    local target = state_dir .. "/" .. pid .. ".json"
    local temporary = target .. ".tmp"
    local file = io.open(temporary, "w")
    if not file then
        mp.msg.error("cannot write " .. temporary)
        return
    end
    file:write(payload)
    file:close()
    os.rename(temporary, target)
end

local function reset()
    started = os.time()
    ended = false
    write_state()
end

mp.register_event("file-loaded", reset)
mp.register_event("end-file", function()
    ended = true
    write_state()
end)
mp.register_event("shutdown", write_state)
mp.add_periodic_timer(1, write_state)
