// Runs the real x86 entry and helper functions in private DLL mappings.
// Does not initialize the engine, launch a game or modify an installed DLL.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>

typedef unsigned char (__thiscall *Handler)(void *, void *, void *);
static BYTE context[16], unit[0xBA0], state[0x760];

static int test(const wchar_t *path, int patched) {
    HMODULE module = LoadLibraryExW(path, NULL, DONT_RESOLVE_DLL_REFERENCES);
    if (!module) { printf("FAIL mapping %lu\n", GetLastError()); return 1; }
    BYTE *image = (BYTE *)module;
    const BYTE expected[] = {(BYTE)(patched ? 0xEB : 0x75), 0x05};
    if (memcmp(image + 0x19857C, expected, 2)) {
        puts("FAIL unexpected branch"); FreeLibrary(module); return 1;
    }
    // Sentinel at movement continuation: return 2 using the original entry's
    // saved EBX and local stack slot. ret 8 preserves the real method ABI.
    const BYTE sentinel[] = {0xB0,0x02,0x5B,0x59,0xC2,0x08,0x00};
    DWORD old;
    if (!VirtualProtect(image + 0x198583, sizeof(sentinel), PAGE_EXECUTE_READWRITE, &old)) return 1;
    memcpy(image + 0x198583, sentinel, sizeof(sentinel));
    DWORD ignored;
    if (!VirtualProtect(image + 0x198583, sizeof(sentinel), old, &ignored)) return 1;
    if (!FlushInstructionCache(GetCurrentProcess(), image + 0x198583, sizeof(sentinel))) return 1;
    *(void **)(context + 8) = unit;
    *(void **)(unit + 0xB9C) = state;
    const int counts[] = {0,1,3,-1,0x7FFFFFFF};
    Handler handler = (Handler)(image + 0x198560);
    for (int i=0; i<5; ++i) {
        *(int *)(state + 0x75C) = counts[i];
        unsigned char result = handler(context, NULL, NULL);
        int expectedResult = patched || counts[i] == 0 ? 2 : 1;
        if (result != expectedResult) { printf("FAIL result %u\n", result); FreeLibrary(module); return 1; }
        printf("PASS %s engagement=%d %s\n", patched ? "patched" : "vanilla", counts[i],
               result == 2 ? "reaches movement continuation" : "returns early");
    }
    FreeLibrary(module);
    return 0;
}

int wmain(int argc, wchar_t **argv) {
    if (argc != 3 || sizeof(void *) != 4) { puts("Usage (x86): test-yari-branch vanilla.dll patched.dll"); return 2; }
    if (test(argv[1],0) || test(argv[2],1)) return 1;
    puts("PASS all 10 real-code branch checks; battle behavior not tested");
    return 0;
}
