// Read-only research harness. Execute original OG group predicates in a private
// uninitialized DLL mapping. Fixtures control only soldier loaded/ready replies.
// No patch, game launch, file write or live process instrumentation occurs.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
typedef unsigned char (__thiscall *Predicate)(void *);
static BYTE task[0x60],squad[0x30],entities[3][0x390];
static void *soldiers[3],*entityTable[0xFC/4],*controllerTable[0x2C/4];
static int map[3],loaded[3],ready[3];
static unsigned char __fastcall loadedFixture(void *self,void *unused) {
    (void)unused;int i=*(int *)((BYTE *)self+0x218);
    return i>=0 && i<3 ? (unsigned char)loaded[i] : 0;
}
static unsigned char __fastcall readyFixture(void *self,void *unused,int action) {
    (void)unused;
    BYTE *entity=(BYTE *)self-0x2F8;
    int i=*(int *)(entity+0x218);
    return action==1 && i>=0 && i<3 ? (unsigned char)ready[i] : 0;
}
struct Case { const char *name; int current,count,groups[3],isLoaded[3],isReady[3],noAction,inactive,expectLoaded,expectReady; };
static const Case cases[]={
    {"all first-rank soldiers loaded and ready",0,3,{0,0,1},{1,1,1},{1,1,1},0,0,1,1},
    {"one current-rank soldier not ready blocks group",0,3,{0,0,1},{1,1,1},{1,0,1},0,0,1,0},
    {"non-current-rank unready soldier ignored",0,3,{0,0,1},{1,1,1},{1,1,0},0,0,1,1},
    {"one first-rank unloaded soldier blocks loaded gate",0,3,{0,0,1},{1,0,1},{1,1,1},0,0,0,1},
    {"later-rank unloaded soldier ignored by first-group gate",0,3,{0,0,1},{1,1,0},{1,1,1},0,0,1,1},
    {"current rank selection changes readiness filter",1,3,{0,0,1},{1,1,1},{1,1,0},0,0,1,0},
    {"first-loaded predicate still selects group zero",1,3,{0,0,1},{0,1,1},{0,1,1},0,0,0,1},
    {"empty squad passes these predicates only",0,0,{0,0,1},{0,0,0},{0,0,0},0,0,1,1},
    {"missing current group is vacuously ready",2,3,{0,0,1},{1,1,1},{0,0,0},0,0,1,1},
    {"active controller without action blocks readiness",0,3,{0,0,1},{1,1,1},{1,1,1},1,0,1,0},
    {"inactive controller follows native ready fallback",0,3,{0,0,1},{1,1,1},{0,0,0},0,1,1,1},
    {"single current-rank soldier waits for readiness",0,1,{0,0,1},{1,1,1},{0,1,1},0,0,1,0}
};
int wmain(int argc,wchar_t **argv) {
    if(argc!=2 || sizeof(void *)!=4) { puts("Usage (x86): inspect-ranked-fire-gates original-engine.dll");return 2; }
    HMODULE m=LoadLibraryExW(argv[1],NULL,DONT_RESOLVE_DLL_REFERENCES);
    if(!m) return 1;
    Predicate firstLoaded=(Predicate)((BYTE *)m+0x178840),allReady=(Predicate)((BYTE *)m+0x17B980);
    entityTable[0xF8/4]=(void *)loadedFixture;
    controllerTable[0x28/4]=(void *)readyFixture;
    for(unsigned c=0;c<sizeof(cases)/sizeof(cases[0]);++c) {
        const Case &v=cases[c];
        memset(task,0,sizeof(task));memset(squad,0,sizeof(squad));memset(entities,0,sizeof(entities));
        *(void **)(task+4)=squad;*(int *)(task+0x40)=v.current;*(void **)(task+0x48)=map;
        *(int *)(squad+0x18)=v.count;*(void **)(squad+0x1C)=soldiers;
        for(int i=0;i<3;++i) {
            soldiers[i]=entities[i];map[i]=v.groups[i];loaded[i]=v.isLoaded[i];ready[i]=v.isReady[i];
            *(void **)entities[i]=entityTable;*(int *)(entities[i]+0x218)=i;
            *(void **)(entities[i]+0x2F8)=controllerTable;
            *(int *)(entities[i]+0x248)=v.noAction ? 0 : 1;
            entities[i][0x384]=(BYTE)(v.inactive ? 0 : 1);
        }
        int a=firstLoaded(task),b=allReady(task);
        if(a!=v.expectLoaded || b!=v.expectReady) { printf("FAIL %s loaded=%d ready=%d\n",v.name,a,b);FreeLibrary(m);return 1; }
        printf("PASS %s | firstLoaded=%d allCurrentReady=%d\n",v.name,a,b);
    }
    FreeLibrary(m);puts("PASS 12 scenarios / 24 original-engine predicate results. No patch applied.");return 0;
}
