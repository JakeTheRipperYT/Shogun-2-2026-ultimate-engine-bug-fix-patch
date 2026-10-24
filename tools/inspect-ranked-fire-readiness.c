// Research only: run original soldier/controller predicates and completion helper.
// Private, uninitialized x86 DLL mapping. No game process or files are modified.
// Input must be the supported vanilla OG engine, not an experimental build.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
typedef unsigned char (__thiscall *Predicate)(void *);
typedef void (__thiscall *Completion)(void *,void *);
static BYTE entity[0x390],sequence[0x30],task[0x60],squad[0x30];
static void *members[2];
static int groups[2];
static int compatible(int action) {
    return action==1 || action==2 || action==13 || action==14 ||
           action==17 || action==18 || action==19 || action==20;
}
int wmain(int argc,wchar_t **argv) {
    if(argc!=2 || sizeof(void *)!=4) { puts("Usage (x86): inspect-ranked-fire-readiness vanilla-engine.dll");return 2; }
    HMODULE m=LoadLibraryExW(argv[1],NULL,DONT_RESOLVE_DLL_REFERENCES);
    if(!m) { printf("Load failed: %lu\n",GetLastError());return 1; }
    BYTE *base=(BYTE *)m;
    const BYTE prefix[]={0x80,0xB9,0x84,0x03,0,0,1};
    if(memcmp(base+0x3CBE40,prefix,sizeof(prefix)) ||
       *(void **)(base+0x15DD1C0+0x28)!=(void *)(base+0x39ECE0)) {
        puts("Unsupported engine bytes/controller vtable");FreeLibrary(m);return 2;
    }
    Predicate ready=(Predicate)(base+0x3CBE40);
    Predicate allReady=(Predicate)(base+0x17B980);
    Completion complete=(Completion)(base+0x38A5E0);
    int checks=0;
    // Execute the real controller callback, including its relocated jump table.
    for(int active=0;active<3;++active) for(int latch=0;latch<3;++latch)
    for(int action=-1;action<=21;++action) {
        memset(entity,0,sizeof(entity));
        *(void **)(entity+0x2F8)=base+0x15DD1C0;
        entity[0x384]=(BYTE)active;entity[0x308]=(BYTE)latch;
        *(int *)(entity+0x248)=action;
        int expected=active!=1 || latch==1 || compatible(action);
        if(ready(entity)!=expected) { printf("FAIL active=%d latch=%d action=%d\n",active,latch,action);return 1; }
        ++checks;
    }
    printf("PASS %d soldier checks through original controller callback (no readiness mock)\n",checks);
    // Completion distinguishes an unfinished sequence from a completed one;
    // status values outside 0..2 set the latch but retain the previous status.
    for(int done=0;done<3;++done) for(int status=0;status<4;++status) {
        memset(entity,0,sizeof(entity));memset(sequence,0,sizeof(sequence));
        BYTE *controller=entity+0x2F8;
        *(int *)(controller+0x1C)=99;
        sequence[8]=(BYTE)done;*(int *)(sequence+0x18)=status;
        complete(controller,sequence);
        int expectedLatch=done==1;
        int expectedStatus=done==1 && status<=2 ? status : 99;
        if(controller[0x10]!=expectedLatch || *(int *)(controller+0x1C)!=expectedStatus) {
            printf("FAIL completion done=%d status=%d\n",done,status);return 1;
        }
        ++checks;
    }
    puts("PASS 12 original sequence-completion/latch checks");
    memset(task,0,sizeof(task));memset(squad,0,sizeof(squad));
    *(void **)(task+4)=squad;*(void **)(task+0x48)=groups;
    *(int *)(squad+0x18)=2;*(void **)(squad+0x1C)=members;
    BYTE second[0x390];memset(second,0,sizeof(second));memset(entity,0,sizeof(entity));
    members[0]=entity;members[1]=second;groups[0]=groups[1]=0;
    *(void **)(entity+0x2F8)=*(void **)(second+0x2F8)=base+0x15DD1C0;
    entity[0x384]=second[0x384]=1;
    *(int *)(entity+0x218)=0;*(int *)(second+0x218)=1;
    *(int *)(entity+0x248)=1;*(int *)(second+0x248)=4;
    if(allReady(task)) { puts("FAIL action 4 did not block current rank");return 1; } ++checks;
    second[0x308]=1;
    if(!allReady(task)) { puts("FAIL latched action 4 still blocks");return 1; } ++checks;
    second[0x308]=0;*(int *)(second+0x248)=17;
    if(!allReady(task)) { puts("FAIL compatible action 17 blocks");return 1; } ++checks;
    puts("PASS 3 group checks with real controller policy");
    printf("PASS %d total native results; no battle or timing claim.\n",checks);
    FreeLibrary(m);return 0;
}
