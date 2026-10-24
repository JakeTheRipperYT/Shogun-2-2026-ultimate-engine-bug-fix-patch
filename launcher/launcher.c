// Launch_Shogun2_Ultimate_Patch.exe
// Starts the patched bootstrap (Shogun2_UB.exe) that sits beside this launcher in the
// Total War: SHOGUN 2 folder. The bootstrap loads UltimatePatch\empire.retail.dll instead of the
// vanilla engine, so the vanilla game stays untouched and launchable from Steam.
// Built without the C runtime: see build.ps1.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <tlhelp32.h>

#define TITLE L"Shogun 2 Ultimate Bug Fix Patch"
#define STEAM_APP_ID L"34330"

static WCHAR root[MAX_PATH * 4], exe[MAX_PATH * 4], engine[MAX_PATH * 4], data[MAX_PATH * 4], cmd[MAX_PATH * 8];
// Static so no CRT memset is needed to zero them.
static STARTUPINFOW startup;
static PROCESS_INFORMATION process;

static void fail(const WCHAR* text) {
    MessageBoxW(0, text, TITLE, MB_ICONERROR);
    ExitProcess(1);
}

static DWORD join(WCHAR* out, DWORD cap, const WCHAR* a, const WCHAR* b) {
    DWORD n = 0;
    while (*a && n + 1 < cap) out[n++] = *a++;
    while (*b && n + 1 < cap) out[n++] = *b++;
    out[n] = 0;
    return *a || *b ? 0 : n;
}

static int steam_running(void) {
    DWORD pid = 0, size = sizeof(pid);
    if (RegGetValueW(HKEY_CURRENT_USER, L"Software\\Valve\\Steam\\ActiveProcess", L"pid", RRF_RT_REG_DWORD, 0, &pid, &size) != ERROR_SUCCESS || !pid) return 0;
    HANDLE h = OpenProcess(SYNCHRONIZE, FALSE, pid);
    if (!h) return 0;
    DWORD alive = WaitForSingleObject(h, 0) == WAIT_TIMEOUT;
    CloseHandle(h);
    return alive;
}

static int same_name(const WCHAR* a, const WCHAR* b) {
    for (;; ++a, ++b) {
        WCHAR x = *a >= L'A' && *a <= L'Z' ? *a + 32 : *a, y = *b >= L'A' && *b <= L'Z' ? *b + 32 : *b;
        if (x != y) return 0;
        if (!x) return 1;
    }
}

// Starting a second copy of the game makes the running one quit, so never do that.
static int game_running(void) {
    HANDLE snap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, 0);
    if (snap == INVALID_HANDLE_VALUE) fail(L"Unable to check running games. Please retry.");
    PROCESSENTRY32W entry;
    entry.dwSize = sizeof(entry);
    int found = 0;
    for (BOOL ok = Process32FirstW(snap, &entry); ok && !found; ok = Process32NextW(snap, &entry))
        found = same_name(entry.szExeFile, L"Shogun2_UB.exe") || same_name(entry.szExeFile, L"shogun2.exe") || same_name(entry.szExeFile, L"Shogun2_UP.exe");
    CloseHandle(snap);
    return found;
}

// Everything after argv[0] in our own command line, so extra arguments reach the game.
static const WCHAR* forwarded_args(void) {
    const WCHAR* p = GetCommandLineW();
    if (*p == L'"') { ++p; while (*p && *p != L'"') ++p; if (*p) ++p; }
    else while (*p && *p != L' ' && *p != L'\t') ++p;
    while (*p == L' ' || *p == L'\t') ++p;
    return p;
}

void entry(void) {
    DWORD n = GetModuleFileNameW(0, root, MAX_PATH * 4);
    if (!n || n >= MAX_PATH * 4 - 1) fail(L"Unable to locate the launcher folder.");
    while (n && root[n - 1] != L'\\') --n;
    root[n] = 0;
    if (!join(exe, MAX_PATH * 4, root, L"Shogun2_UB.exe") || !join(engine, MAX_PATH * 4, root, L"UltimatePatch\\empire.retail.dll") ||
        !join(data, MAX_PATH * 4, root, L"UltimatePatch\\data\\data.pack"))
        fail(L"The game folder path is too long.");
    if (GetFileAttributesW(exe) == INVALID_FILE_ATTRIBUTES || GetFileAttributesW(engine) == INVALID_FILE_ATTRIBUTES ||
        GetFileAttributesW(data) == INVALID_FILE_ATTRIBUTES)
        fail(L"The Ultimate Patch is not installed in this folder.\n\nRun the Shogun 2 Ultimate Bug Fix Patch installer and choose Install / Update. "
             L"Keep this launcher in the Total War: SHOGUN 2 folder.");
    if (game_running())
        fail(L"Shogun 2 is already running.\n\nClose it before launching the Ultimate Patch.");
    if (!steam_running())
        fail(L"Steam is not running.\n\nStart Steam, sign in, then launch the Ultimate Patch again.");
    if (!SetEnvironmentVariableW(L"SteamAppId", STEAM_APP_ID) || !SetEnvironmentVariableW(L"SteamGameId", STEAM_APP_ID))
        fail(L"Unable to prepare the Steam environment.");

    const WCHAR* args = forwarded_args();
    DWORD c = 0;
    cmd[c++] = L'"';
    for (const WCHAR* s = exe; *s; ++s) cmd[c++] = *s;
    cmd[c++] = L'"';
    if (*args) { cmd[c++] = L' '; while (*args && c + 1 < MAX_PATH * 8) cmd[c++] = *args++; }
    if (*args) fail(L"The launch arguments are too long.");
    cmd[c] = 0;

    startup.cb = sizeof(startup);
    if (!CreateProcessW(exe, cmd, 0, 0, FALSE, 0, 0, root, &startup, &process))
        fail(L"Unable to start the Ultimate Patch. Make sure the game is installed and Steam is running.");
    CloseHandle(process.hThread);
    CloseHandle(process.hProcess);
    ExitProcess(0);
}
