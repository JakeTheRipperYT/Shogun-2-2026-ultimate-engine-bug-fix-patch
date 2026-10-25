// Compile as x86 C++ (/TP). Execute real OG movement eligibility control flow
// in private, uninitialized DLL mappings, with controlled ability/action/final
// eligibility fixtures. No installed files or live processes are modified.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>

typedef unsigned char (__thiscall *Eligibility)(void *);
static BYTE unit[0xEE0], parent[16], battle[0xB8], mode[0x18];
static void *abilityTable[2], *actionTable[0xE0/4], *actionObject[1];
static int active, actionAllowed, finalAllowed, abilityCalls, actionCalls, finalCalls;
static unsigned char __fastcall ability(void *self, void *unused, int id) {
    (void)unused;
    if (self != unit + 0xED4 || id != 0x39) return 0xFF;
    ++abilityCalls;
    return (unsigned char)active;
}
static unsigned char __fastcall action(void *self, void *unused) {
    (void)unused;
    if (self != actionObject) return 0xFF;
    ++actionCalls;
    return (unsigned char)actionAllowed;
}
static unsigned char __fastcall finalCheck(void *self, void *unused) {
    (void)unused;
    if (self != unit) return 0xFF;
    ++finalCalls;
    return (unsigned char)finalAllowed;
}

static int test(const wchar_t *path, int patched) {
    HMODULE module = LoadLibraryExW(path, NULL, DONT_RESOLVE_DLL_REFERENCES);
    if (!module) { printf("FAIL DLL mapping %lu\n",GetLastError()); return 1; }
    BYTE *image=(BYTE *)module;
    const BYTE original[]={0x75,0x45}, changed[]={0x90,0x90};
    if (memcmp(image+0x15C408,patched ? changed : original,2)) {
        puts("FAIL unexpected gate bytes"); FreeLibrary(module); return 1;
    }
    BYTE jump[]={0xB8,0,0,0,0,0xFF,0xE0}; // mov eax,callback / jmp eax
    void *callback=(void *)finalCheck;
    memcpy(jump+1,&callback,4);
    DWORD old,ignored;
    if (!VirtualProtect(image+0x15CB40,sizeof(jump),PAGE_EXECUTE_READWRITE,&old)) return 1;
    memcpy(image+0x15CB40,jump,sizeof(jump));
    if (!VirtualProtect(image+0x15CB40,sizeof(jump),old,&ignored)) return 1;
    if (!FlushInstructionCache(GetCurrentProcess(),image+0x15CB40,sizeof(jump))) return 1;
    abilityTable[1]=(void *)ability;
    actionTable[0xDC/4]=(void *)action;
    actionObject[0]=actionTable;
    *(void **)(unit+0xED4)=abilityTable;
    *(void **)(unit+0x14)=parent;
    *(void **)(parent+8)=battle;
    *(void **)(battle+0xB4)=mode;
    *(void **)(unit+0xBA0)=actionObject;
    Eligibility fn=(Eligibility)(image+0x15C3F0);
    const int phases[]={0,5,6,7,8,9};
    int cases=0;
    for(active=0;active<2;++active) for(int p=0;p<6;++p)
    for(int count=0;count<2;++count) for(actionAllowed=0;actionAllowed<2;++actionAllowed)
    for(finalAllowed=0;finalAllowed<2;++finalAllowed) {
        *(int *)(mode+0x14)=phases[p];
        *(int *)(unit+0xBA8)=count;
        abilityCalls=actionCalls=finalCalls=0;
        int phaseRestricted=phases[p]>=5 && phases[p]<=8;
        int blocked=!patched && active;
        int actionExpected=!blocked && phaseRestricted && count;
        int finalExpected=!blocked && phaseRestricted && (!count || actionAllowed);
        int expected=blocked ? 0 : !phaseRestricted ? 1 : count && !actionAllowed ? 0 : finalAllowed;
        unsigned char result=fn(unit);
        if(result!=expected || abilityCalls!=1 || actionCalls!=actionExpected || finalCalls!=finalExpected) {
            printf("FAIL %s active=%d phase=%d count=%d action=%d final=%d result=%u expected=%d calls=%d/%d/%d\n",
                patched ? "patched" : "vanilla",active,phases[p],count,actionAllowed,finalAllowed,
                result,expected,abilityCalls,actionCalls,finalCalls);
            FreeLibrary(module); return 1;
        }
        ++cases;
    }
    printf("PASS %s: %d real eligibility cases; original phase/action/final checks preserved\n",patched ? "patched" : "vanilla",cases);
    FreeLibrary(module);
    return 0;
}

int wmain(int argc,wchar_t **argv) {
    if(argc!=3 || sizeof(void *)!=4) { puts("Usage (x86): test-kneel-eligibility vanilla.dll patched.dll"); return 2; }
    if(test(argv[1],0) || test(argv[2],1)) return 1;
    puts("PASS all 192 native eligibility checks; full battle behavior remains untested");
    return 0;
}
