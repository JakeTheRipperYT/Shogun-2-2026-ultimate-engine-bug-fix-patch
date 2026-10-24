// OG research: execute original transition construction, goal mapping, sequence
// completion and rank request construction with controlled object fixtures.
// One downstream dispatch call is intercepted ONLY in the private DLL mapping.
// No on-disk DLL or live game is changed. Build as x86 C++ with /TP /W4 /WX.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
typedef void *(__thiscall *Construct)(void *);
typedef DWORD *(__thiscall *Resolve)(void *,int,int,DWORD *);
typedef void (__thiscall *Update)(void *);
typedef void (__thiscall *Prepare)(void *,void *,BYTE);
typedef void *(__thiscall *ControllerConstruct)(void *,void *,void *);
typedef BYTE (__thiscall *Dispatch)(void *);
typedef void *(__thiscall *StateEvaluate)(void *,void *);
typedef const char *(__thiscall *StateName)(void *);
static BYTE matrix[93*93*28],entity[0x700],sequence[0x90];
static BYTE world[0xB8],kind[0x20],owner[0x10],animHolder[0x30],animData[0xA08];
static BYTE task[0x60],request[0x50];
static void *capturedSoldier;
static void *entityTable[0x140/4],*sequenceTable[0x20/4];
static int captures,starts,fixtureLoaded;
static void *__fastcall noAttachment(void *self,void *unused) {
    (void)self;(void)unused;return NULL;
}
static BYTE __fastcall falseFixture(void *self,void *unused) {
    (void)self;(void)unused;return 0;
}
static BYTE __fastcall loadedFixture(void *self,void *unused) {
    (void)self;(void)unused;return (BYTE)fixtureLoaded;
}
static void __fastcall ownerNotification(void *self,void *unused) {
    (void)self;(void)unused;
}
static void __fastcall startFixture(void *self,void *unused) {
    (void)unused;++starts;((BYTE *)self)[0x70]=1;
}
static void __fastcall capture(void *soldier,void *unused,void *data) {
    (void)unused;capturedSoldier=soldier;memcpy(request,data,sizeof(request));++captures;
}
struct Edge {int from,to,animation,optional;};
static const Edge edges[]={
    {0,8,4,1},{4,8,62,1},{8,9,95,0},{9,8,107,0},
    {14,8,125,1},{15,9,128,1},{16,8,135,1},{17,9,139,1}
};
int wmain(int argc,wchar_t **argv) {
    setvbuf(stdout,NULL,_IONBF,0);
    if(argc!=2 || sizeof(void *)!=4) {puts("Usage (x86): inspect-ranked-fire-sequences vanilla-engine.dll");return 2;}
    HMODULE m=LoadLibraryExW(argv[1],NULL,DONT_RESOLVE_DLL_REFERENCES);
    if(!m) return 2;
    BYTE *base=(BYTE *)m;
    Construct init=(Construct)(base+0x34F7E0);
    Resolve resolve=(Resolve)(base+0x3A8A40);
    Update mapGoal=(Update)(base+0x3E4850),readySequence=(Update)(base+0x3EF1E0);
    Prepare prepare=(Prepare)(base+0x188290);
    // Exact call used by this version: FUN_10188290 -> FUN_103DB8F0.
    BYTE *call=base+0x1882FF,saved[5];memcpy(saved,call,5);
    LONG displacement=0;memcpy(&displacement,call+1,4);
    if(call[0]!=0xE8 || call+5+displacement!=base+0x3DB8F0) {
        puts("Unsupported dispatch call");FreeLibrary(m);return 2;
    }
    int checks=0;
    for(int i=0;i<12;++i) {
        void *state=base+0x179A0F0+i*4;
        void **table=*(void ***)state;
        const char *name=((StateName)table[4])(state);
        printf("Firearm state %08lX: %s\n",0x1179A0F0UL+(DWORD)i*4,name);
    }
    puts("Initializing transition matrix in fixture memory");
    init(matrix);
    puts("Transition matrix initialized");
    for(unsigned i=0;i<sizeof(edges)/sizeof(edges[0]);++i) {
        const Edge &e=edges[i];DWORD rng=1234;
        DWORD *r=resolve(matrix,e.from,e.to,&rng);
        if(r[0]!=(DWORD)e.animation || ((BYTE *)r)[4]!=e.optional) {
            printf("FAIL transition %d -> %d\n",e.from,e.to);return 1;
        }
        const char *name=*(const char **)(base+0x1692640+e.animation*24+4);
        printf("PASS mode %d -> %d: animation %d %s, optional=%d\n",e.from,e.to,e.animation,name,e.optional);
        ++checks;
    }
    const int goals[]={8,9,14,15,16,17},states[]={18,19,29,30,31,32};
    for(unsigned i=0;i<sizeof(goals)/sizeof(goals[0]);++i) {
        memset(entity,0,sizeof(entity));*(int *)(entity+0x1F0)=goals[i];mapGoal(entity);
        if(*(int *)(entity+0x1D0)!=states[i]) {puts("FAIL goal map");return 1;}++checks;
    }
    puts("PASS 6 goal-to-state mappings");
    // Use ordinary kind 0/3 eligibility through the real helper, no link bypass.
    // Same goal makes the stance-request helper return before clip access.
    // This isolates whether the completion test itself requires clip absence.
    for(int mode=0;mode<2;++mode) for(int matched=0;matched<2;++matched)
    for(int clip=0;clip<2;++clip) for(int unitKind=0;unitKind<=3;unitKind+=3) {
        memset(entity,0,sizeof(entity));memset(sequence,0,sizeof(sequence));
        memset(world,0,sizeof(world));memset(kind,0,sizeof(kind));
        memset(owner,0,sizeof(owner));memset(animHolder,0,sizeof(animHolder));
        memset(animData,0,sizeof(animData));
        entityTable[0xBC/4]=(void *)noAttachment;*(void **)entity=entityTable;
        *(void **)(sequence+4)=entity;*(void **)(sequence+0x14)=owner;
        *(void **)(owner+8)=world;*(void **)(world+0xB4)=kind;
        *(int *)(kind+0x14)=unitKind;*(int *)(sequence+0x1C)=mode;
        *(void **)(entity+0x23C)=animHolder;*(void **)animHolder=animHolder+4;
        *(void **)(animHolder+4+0x28)=animData;*(int *)(animData+0xA04)=1;
        *(int *)(entity+0x1F0)=8+mode;
        *(int *)(entity+0x1D0)=matched ? 18+mode : 0;
        *(DWORD *)(entity+0x474)=clip ? 0x12345678 : 0;
        readySequence(sequence);
        if(sequence[8]!=(BYTE)matched) {printf("FAIL mode=%d matched=%d clip=%d kind=%d\n",mode,matched,clip,unitKind);return 1;}
        ++checks;
    }
    puts("PASS 16 ready-sequence cases: matched state completes even with a current clip marker");
    DWORD protection=0;
    if(!VirtualProtect(call,5,PAGE_EXECUTE_READWRITE,&protection)) return 2;
    displacement=(LONG)((BYTE *)(void *)capture-(call+5));memcpy(call+1,&displacement,4);
    FlushInstructionCache(GetCurrentProcess(),call,5);
    int requestCases=0,map=0;
    for(int groupCount=1;groupCount<=3;++groupCount)
    for(int group=0;group<groupCount;++group)
    for(int fired=0;fired<2;++fired) for(int first=0;first<2;++first)
    for(int followup=0;followup<2;++followup) {
        memset(task,0,sizeof(task));memset(entity,0,sizeof(entity));
        *(int *)(task+0x38)=groupCount;*(void **)(task+0x48)=&map;map=group;
        task[0x44]=(BYTE)fired;task[0x45]=(BYTE)first;captures=0;
        prepare(task,entity,(BYTE)followup);
        int mode=(followup ? fired : !first) && group<groupCount-1;
        if(captures!=1 || capturedSoldier!=entity || *(int *)(request+0x20)!=5 ||
           *(int *)(request+0x24)!=mode || request[0x30]!=1) {
            puts("FAIL get-ready request or first-cycle stance guard");return 1;
        }
        ++requestCases;++checks;
    }
    memcpy(call,saved,5);DWORD ignored=0;VirtualProtect(call,5,protection,&ignored);
    FlushInstructionCache(GetCurrentProcess(),call,5);
    printf("PASS %d rank get-ready request cases, including first-cycle stance guards\n",requestCases);
    // Audit the claimed wait on entry using the actual request, constructor and
    // owner lifecycle. Type 5 has no preliminary handle at controller+0x54.
    // Only the final start implementation is replaced with a recording fixture.
    BYTE *start=base+0x392740,startSaved[5];memcpy(startSaved,start,5);
    if(!VirtualProtect(start,5,PAGE_EXECUTE_READWRITE,&protection)) return 2;
    start[0]=0xE9;displacement=(LONG)((BYTE *)(void *)startFixture-(start+5));
    memcpy(start+1,&displacement,4);FlushInstructionCache(GetCurrentProcess(),start,5);
    for(int previousDone=0;previousDone<2;++previousDone) {
        memset(entity,0,sizeof(entity));memset(owner,0,sizeof(owner));memset(world,0,sizeof(world));
        entityTable[0x10C/4]=(void *)falseFixture;
        entityTable[0x13C/4]=(void *)ownerNotification;
        sequenceTable[0x1C/4]=(void *)falseFixture;
        *(void **)entity=entityTable;*(void **)(entity+0x28)=owner;
        *(void **)(owner+8)=world;*(void **)(entity+0x2F0)=entity;
        *(void **)(entity+0x250)=sequenceTable;entity[0x258]=(BYTE)previousDone;
        ControllerConstruct ctor=(ControllerConstruct)(base+0x350F10);
        ctor(entity+0x2F8,entity+0x2F0,request);
        if(*(DWORD *)(entity+0x2F8+0x54)!=0 || entity[0x308]!=0) {
            puts("FAIL type-5 constructor fields");return 1;
        }
        starts=0;Dispatch dispatch=(Dispatch)(base+0x3EFC70);dispatch(entity+0x2F0);
        if(starts!=1 || entity[0x385]!=1 || entity[0x2F8+0x70]!=1) {
            puts("FAIL ordinary type-5 request did not start on entry");return 1;
        }
        ++checks;
    }
    memcpy(start,startSaved,5);VirtualProtect(start,5,protection,&ignored);
    FlushInstructionCache(GetCurrentProcess(),start,5);
    puts("PASS 2 owner-lifecycle cases: ordinary type-5 entry starts with previous sequence done=0 OR 1");
    // Actual firearm sequence STOP_STATE, not the non-FIRE fallback tested above.
    // Execute its original evaluator, its real delay/clip predicate and getters.
    StateEvaluate stop=(StateEvaluate)(base+0x3B2BA0);
    int stopCases=0;
    float secondsPerTick=*(float *)(base+0x15B2448);
    for(int stateFlag=0;stateFlag<2;++stateFlag)
    for(int clip=0;clip<2;++clip) for(int elapsed=0;elapsed<2;++elapsed) {
        memset(entity,0,sizeof(entity));memset(sequence,0,sizeof(sequence));
        *(void **)sequence=base+0x15E10D0;
        *(void **)(sequence+4)=entity;*(void **)(sequence+0x14)=owner;
        *(void **)(owner+8)=world;*(DWORD *)(world+0x50)=300;
        *(int *)(sequence+0x44)=5;*(float *)(sequence+0x74)=300*secondsPerTick;
        *(float *)(sequence+0x50)=elapsed ? 0.0f : 1.0f;
        entity[0x11F]=(BYTE)stateFlag;*(DWORD *)(entity+0x474)=clip ? 0x12345678 : 0;
        void *next=stop(NULL,sequence+0x1C);
        void *expected=stateFlag && !clip && elapsed ? base+0x179A0F4 : NULL;
        if(next!=expected) {printf("FAIL firearm STOP flag=%d clip=%d elapsed=%d\n",stateFlag,clip,elapsed);return 1;}
        ++stopCases;++checks;
    }
    printf("PASS %d firearm STOP_STATE cases: flag + clip absence + elapsed delay are all required\n",stopCases);
    StateEvaluate readyState=(StateEvaluate)(base+0x3B2C80);
    for(fixtureLoaded=0;fixtureLoaded<2;++fixtureLoaded) {
        memset(entity,0,sizeof(entity));memset(sequence,0,sizeof(sequence));
        entityTable[0xF8/4]=(void *)loadedFixture;*(void **)entity=entityTable;
        *(void **)sequence=base+0x15E10D0;*(void **)(sequence+4)=entity;
        *(int *)(sequence+0x44)=5;
        void *next=readyState(NULL,sequence+0x1C);
        void *expected=fixtureLoaded ? base+0x179A11C : base+0x179A114;
        if(next!=expected) {puts("FAIL firearm START_STATE type-5 loaded routing");return 1;}++checks;
    }
    puts("PASS 2 firearm START_STATE cases: type-5 loaded -> FINISH, unloaded -> RELOAD_STATE");
    // Event-free clip fixtures use the actual original frame advancement and
    // cancellation code. No hook is needed: a null clip+8 omits motion events.
    Update advanceClip=(Update)(base+0x3F0370);
    const int lengths[]={1,10,93};
    for(int idle=141;idle<=152;idle+=11) for(unsigned n=0;n<3;++n) {
        DWORD clipObject[3]={0};BYTE clipData[0x68]={0};
        memset(entity,0,sizeof(entity));memset(sequence,0,sizeof(sequence));
        *(void **)sequence=base+0x15E10D0;*(void **)(sequence+4)=entity;
        *(void **)(sequence+0x14)=owner;*(void **)(owner+8)=world;
        *(DWORD *)(world+0x50)=300;*(int *)(sequence+0x44)=5;
        clipObject[0]=(DWORD)idle;clipObject[1]=(DWORD)clipData;
        *(int *)(clipData+0x64)=lengths[n];*(void **)(entity+0x474)=clipObject;
        entity[0x11F]=1;
        for(int tick=0;tick<lengths[n];++tick) {
            if(stop(NULL,sequence+0x1C)!=NULL) {puts("FAIL active idle clip did not block STOP");return 1;}
            advanceClip(entity);
        }
        if(*(void **)(entity+0x474)!=NULL || stop(NULL,sequence+0x1C)!=base+0x179A0F4) {
            puts("FAIL idle clip completion did not unblock STOP");return 1;
        }
        ++checks;
    }
    puts("PASS 6 idle-clip progression cases: STOP waits for all remaining clip ticks, then advances");
    printf("PASS %d total native results; no battle timing or fix claim.\n",checks);
    FreeLibrary(m);return 0;
}
