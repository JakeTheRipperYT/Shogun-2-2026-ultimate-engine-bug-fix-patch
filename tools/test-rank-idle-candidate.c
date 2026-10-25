// Execute the actual OG rank preparation entry in two private DLL mappings.
// Only the downstream request dispatch is intercepted. Native cancellation and
// the candidate's full PIC detour execute unchanged. No live/game files change.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
typedef void (__thiscall *Prepare)(void *,void *,BYTE);
typedef void *(__thiscall *StateEvaluate)(void *,void *);
static BYTE task[0x60],soldier[0x700],beforeSoldier[0x700],beforeTask[0x60],request[0x50];
static void *capturedSoldier;
static int captures;
static BYTE loaded;
static void *entityTable[0x100/4];
static BYTE __fastcall loadedFixture(void *self,void *unused) {(void)self;(void)unused;return loaded;}
static void *abiFunction,*abiTask,*abiSoldier;
static DWORD abiBefore,abiAfter,abiEBX,abiESI,abiEDI,abiEBP;
static void checkABI() {
    __asm {
        push ebx
        push esi
        push edi
        push ebp
        mov abiBefore,esp
        mov ebx,12345678h
        mov esi,23456789h
        mov edi,3456789Ah
        mov ebp,456789ABh
        push 0
        mov eax,abiSoldier
        push eax
        mov ecx,abiTask
        call dword ptr [abiFunction]
        mov abiAfter,esp
        mov abiEBX,ebx
        mov abiESI,esi
        mov abiEDI,edi
        mov abiEBP,ebp
        pop ebp
        pop edi
        pop esi
        pop ebx
    }
}
static void __fastcall dispatchFixture(void *self,void *unused,void *data) {
    (void)unused;capturedSoldier=self;memcpy(request,data,sizeof(request));++captures;
}
struct Guard {const char *name;int rank,first,fired,followup,current;};
static const Guard guards[]={
    {"initial ranked preparation",1,1,0,0,0},
    {"different task class",0,1,0,0,0},
    {"first cycle finished",1,0,0,0,0},
    {"first volley already dispatched",1,1,1,0,0},
    {"follow-up call",1,1,0,1,0},
    {"later current rank",1,1,0,0,1},
    {"noncanonical first flag",1,2,0,0,0},
    {"noncanonical fired flag",1,1,2,0,0}
};
static const int clips[]={-1,0,1,4,5,95,107,124,125,126,127,128,129,130,132,133,134,135,136,137,138,139,140,
    141,142,143,144,145,146,147,148,149,150,151,152,153,154,155,156,157,158,178,205,1187,
    (-2147483647-1),2147483647};
static int run(HMODULE module,int patched) {
    BYTE *base=(BYTE *)module,*call=base+0x1882FF;
    const BYTE original[]={0x83,0xEC,0x50,0x8B,0xC1};
    if(patched ? base[0x188290]!=0xE9 : memcmp(base+0x188290,original,5)!=0) {
        puts("FAIL entry mismatch");return 1;
    }
    BYTE saved[5];memcpy(saved,call,5);DWORD protection=0;
    if(!VirtualProtect(call,5,PAGE_EXECUTE_READWRITE,&protection)) return 1;
    LONG displacement=(LONG)((BYTE *)(void *)dispatchFixture-(call+5));
    call[0]=0xE8;memcpy(call+1,&displacement,4);FlushInstructionCache(GetCurrentProcess(),call,5);
    Prepare prepare=(Prepare)(base+0x188290);
    int cases=0,cancelled=0,group=0;
    for(unsigned g=0;g<sizeof(guards)/sizeof(guards[0]);++g)
    for(unsigned c=0;c<sizeof(clips)/sizeof(clips[0]);++c)
    for(int laterMember=0;laterMember<2;++laterMember) {
        const Guard &v=guards[g];DWORD clipObject[3]={(DWORD)clips[c],0,0};
        memset(task,0,sizeof(task));memset(soldier,0x5A,sizeof(soldier));
        *(void **)task=base+(v.rank ? 0x15C1048 : 0x15C0FB4);
        task[0x45]=(BYTE)v.first;task[0x44]=(BYTE)v.fired;
        *(int *)(task+0x40)=v.current;*(int *)(task+0x38)=3;
        group=laterMember ? 2 : 0;*(void **)(task+0x48)=&group;
        *(int *)(soldier+0x218)=0;
        *(void **)(soldier+0x474)=clips[c]==-1 ? NULL : clipObject;
        memcpy(beforeSoldier,soldier,sizeof(soldier));memcpy(beforeTask,task,sizeof(task));
        captures=0;prepare(task,soldier,(BYTE)v.followup);
        int expectedCancel=patched && v.rank && v.first==1 && v.fired==0 &&
            v.followup==0 && v.current==0 && clips[c]>=141 && clips[c]<=157;
        if(expectedCancel) *(void **)(beforeSoldier+0x474)=NULL;
        int expectedMode=(v.followup ? v.fired!=0 : v.first==0) && group<2;
        if(captures!=1 || capturedSoldier!=soldier || *(int *)(request+0x20)!=5 ||
           *(int *)(request+0x24)!=expectedMode || request[0x30]!=1 ||
           *(DWORD *)(request+0x34)!=0 || memcmp(soldier,beforeSoldier,sizeof(soldier)) ||
           memcmp(task,beforeTask,sizeof(task))) {
            printf("FAIL %s: %s clip=%d memberGroup=%d expectedCancel=%d\n",patched ? "candidate" : "vanilla",v.name,clips[c],group,expectedCancel);
            return 1;
        }
        ++cases;cancelled+=expectedCancel;
    }
    // Explicit callee-save and stack sentinels around the real preparation entry.
    DWORD abiClip[3]={141,0,0};memset(task,0,sizeof(task));memset(soldier,0,sizeof(soldier));
    *(void **)task=base+0x15C1048;task[0x45]=1;*(int *)(task+0x38)=3;
    group=0;*(void **)(task+0x48)=&group;*(void **)(soldier+0x474)=abiClip;
    abiFunction=(void *)prepare;abiTask=task;abiSoldier=soldier;checkABI();
    if(abiBefore!=abiAfter || abiEBX!=0x12345678 || abiESI!=0x23456789 ||
       abiEDI!=0x3456789A || abiEBP!=0x456789AB) {puts("FAIL callee-save/ESP sentinels");return 1;}
    ++cases;
    // Integrate actual preparation with original firearm STOP and START gates.
    StateEvaluate stop=(StateEvaluate)(base+0x3B2BA0),start=(StateEvaluate)(base+0x3B2C80);
    const int integrationClips[]={-1,141,152,133,95};
    int integrationCases=0;
    for(unsigned c=0;c<sizeof(integrationClips)/sizeof(integrationClips[0]);++c)
    for(int movingDone=0;movingDone<2;++movingDone) for(int elapsed=0;elapsed<2;++elapsed)
    for(loaded=0;loaded<2;++loaded) {
        BYTE sequence[0x90]={0},owner[0x10]={0},world[0x60]={0};
        DWORD clipObject[3]={(DWORD)integrationClips[c],0,0};
        memset(task,0,sizeof(task));memset(soldier,0,sizeof(soldier));
        *(void **)task=base+0x15C1048;task[0x45]=1;*(int *)(task+0x38)=3;
        group=0;*(void **)(task+0x48)=&group;
        entityTable[0xF8/4]=(void *)loadedFixture;*(void **)soldier=entityTable;
        soldier[0x11F]=(BYTE)movingDone;
        *(void **)(soldier+0x474)=integrationClips[c]==-1 ? NULL : clipObject;
        prepare(task,soldier,0);
        *(void **)sequence=base+0x15E10D0;*(void **)(sequence+4)=soldier;
        *(void **)(sequence+0x14)=owner;*(void **)(owner+8)=world;
        *(DWORD *)(world+0x50)=300;*(int *)(sequence+0x44)=5;
        *(float *)(sequence+0x74)=300*(*(float *)(base+0x15B2448));
        *(float *)(sequence+0x50)=elapsed ? 0.0f : 1.0f;
        int empty=integrationClips[c]==-1 || (patched && integrationClips[c]>=141 && integrationClips[c]<=157);
        int expected=movingDone && elapsed && empty;
        void *next=stop(NULL,sequence+0x1C);
        if(next!=(expected ? base+0x179A0F4 : NULL)) {puts("FAIL preparation bypassed STOP condition");return 1;}
        if(expected && start(NULL,sequence+0x1C)!=(loaded ? base+0x179A11C : base+0x179A114)) {
            puts("FAIL preparation bypassed loaded/reload routing");return 1;
        }
        ++integrationCases;++cases;
    }
    memcpy(call,saved,5);DWORD ignored=0;VirtualProtect(call,5,protection,&ignored);
    FlushInstructionCache(GetCurrentProcess(),call,5);
    printf("PASS %s: %d real-entry cases, %d expected idle cancellations; request/stance and all other fixture bytes preserved\n",patched ? "candidate" : "vanilla",cases,cancelled);
    printf("PASS %s: ESP/EBX/ESI/EDI/EBP sentinels and %d original STOP/START integration cases\n",patched ? "candidate" : "vanilla",integrationCases);
    return 0;
}
int wmain(int argc,wchar_t **argv) {
    setvbuf(stdout,NULL,_IONBF,0);
    if(argc!=3 || sizeof(void *)!=4) {puts("Usage (x86): test-rank-idle-candidate vanilla.dll candidate.dll");return 2;}
    HMODULE original=LoadLibraryExW(argv[1],NULL,DONT_RESOLVE_DLL_REFERENCES);
    HMODULE candidate=LoadLibraryExW(argv[2],NULL,DONT_RESOLVE_DLL_REFERENCES);
    if(!original || !candidate || original==candidate) {puts("FAIL distinct private mappings");return 2;}
    printf("ASLR mappings: vanilla=%p candidate=%p\n",original,candidate);
    int failed=run(original,0) || run(candidate,1);
    FreeLibrary(candidate);FreeLibrary(original);
    if(!failed) puts("PASS guarded candidate matrix; live battle behavior still requires capture/comparison.");
    return failed;
}
