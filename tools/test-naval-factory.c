// x86 C++ (/TP). Runs the real defender factory and patched adapter in private
// uninitialized DLL mappings. Allocation, construction and publication are
// controlled fixtures: no live battle/game files are changed.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
typedef void (__thiscall *Factory)(void *);
static BYTE root[0x148], analyzer[0x160], groups[4][0x6C], pool[2][0x178];
static void *groupList[4];
static int allocs,lands,holdings,attacks,registered,finalized,failSize,errors;
static int targets[2],sizes[2];
static void *objects[2];
static void *__cdecl allocate(int size) {
    if(allocs>=2) { ++errors;return NULL; }
    sizes[allocs]=size;
    return size==failSize ? (++allocs,(void *)NULL) : (void *)pool[allocs++];
}
static void *__cdecl finalize(void *obj,int size) {
    if(finalized>=allocs || sizes[finalized]!=size) ++errors;
    ++finalized;return obj;
}
static void __fastcall append(void *self,void *unused,void *obj) {
    (void)unused;
    if(self!=root+0x3C || registered>=2) { ++errors;return; }
    objects[registered++]=obj;
}
static int argsOK(void *self,void *battleRef,void *parent) {
    return (self==pool[0] || self==pool[1]) && battleRef==root+4 && parent==root;
}
static void *__fastcall holding(void *self,void *unused,void *battleRef,void *parent) {
    (void)unused;if(!argsOK(self,battleRef,parent)) ++errors;
    ++holdings;return self;
}
static void *__fastcall attack(void *self,void *unused,void *battleRef,void *parent,int target) {
    (void)unused;if(!argsOK(self,battleRef,parent) || attacks>=2) ++errors;
    else targets[attacks]=target;
    ++attacks;return self;
}
static void *__fastcall land(void *self,void *unused,void *battleRef,void *parent,void *guard) {
    (void)unused;if(!argsOK(self,battleRef,parent) || guard!=(void *)1) ++errors;
    ++lands;return self;
}
static int redirect(BYTE *at,void *callback) {
    BYTE j[]={0xB8,0,0,0,0,0xFF,0xE0};memcpy(j+1,&callback,4);
    DWORD old,unused;
    if(!VirtualProtect(at,sizeof(j),PAGE_EXECUTE_READWRITE,&old)) return 0;
    memcpy(at,j,sizeof(j));
    return VirtualProtect(at,sizeof(j),old,&unused) && FlushInstructionCache(GetCurrentProcess(),at,sizeof(j));
}
struct Scenario { int guard,landCount,shipCount,fail,groupCount,ships[4],ids[4],expected; };
static const Scenario cases[]={
    {0,1,1,0,0,{0},{0},77},
    {1,0,0,0,0,{0},{0},77},
    {1,0,1,0,0,{0},{0},77},
    {1,0,1,0,1,{0},{10},77},
    {1,0,1,0,1,{6},{42},42},
    {1,0,1,0,2,{0,8},{10,99},99},
    {1,0,1,0,2,{5,7},{42,99},42},
    {1,0,1,0,4,{0,0,0,2},{1,2,3,123},123},
    {1,0,1,0,4,{0,0,0,0},{1,2,3,4},77},
    {1,1,0,0,0,{0},{0},77},
    {1,1,1,0,2,{0,8},{10,99},99},
    {1,0,1,0x4C,1,{6},{42},42},
    {1,1,1,0x178,1,{6},{42},42},
    {1,1,1,0x4C,1,{6},{42},42}
};
static int test(HMODULE module,int patched) {
    BYTE *image=(BYTE *)module;
    DWORD wanted=patched ? 0x115A0D20 : 0x10546690;
    if(image[0x4D1636]!=0xE8 || (DWORD)(0x104D163B+*(int *)(image+0x4D1637))!=wanted) return 1;
    if(!redirect(image+0xF7440,(void *)allocate) || !redirect(image+0x4F5680,(void *)finalize)
       || !redirect(image+0xB5500,(void *)append) || !redirect(image+0x546690,(void *)holding)
       || !redirect(image+0x1CA070,(void *)attack) || !redirect(image+0x1CA1C0,(void *)land)) return 1;
    Factory factory=(Factory)(image+0x4D15D0);
    for(unsigned i=0;i<sizeof(cases)/sizeof(cases[0]);++i) {
        const Scenario &c=cases[i];
        memset(root,0,sizeof(root));memset(analyzer,0,sizeof(analyzer));memset(groups,0,sizeof(groups));
        memset(pool,0,sizeof(pool));memset(objects,0,sizeof(objects));
        allocs=lands=holdings=attacks=registered=finalized=errors=0;failSize=c.fail;
        *(void **)(root+0x64)=c.guard ? (void *)1 : NULL;
        *(int *)(root+0x28)=c.landCount;*(int *)(root+0x14)=c.shipCount;
        *(int *)(root+0x144)=77;*(void **)(root+0x30)=analyzer;
        *(int *)(analyzer+0x158)=c.groupCount;*(void **)(analyzer+0x15C)=c.groupCount ? groupList : NULL;
        for(int j=0;j<c.groupCount;++j) {
            *(int *)(groups[j]+0x48)=c.ships[j];*(int *)(groups[j]+0x68)=c.ids[j];groupList[j]=groups[j];
        }
        factory(root);
        int naval=c.guard && c.shipCount && c.fail!=0x4C;
        int landExpected=c.guard && c.landCount && c.fail!=0x178;
        int allocationExpected=c.guard ? c.landCount+c.shipCount : 0;
        if(errors || allocs!=allocationExpected || registered!=allocs || finalized!=allocs
           || lands!=landExpected || holdings!=(patched ? 0 : naval) || attacks!=(patched ? naval : 0)
           || (patched && naval && targets[0]!=c.expected)) {
            printf("FAIL %s scenario %u errors=%d allocations=%d land=%d holding=%d attack=%d\n",
                patched ? "patched" : "vanilla",i,errors,allocs,lands,holdings,attacks);return 1;
        }
        for(int j=0;j<registered;++j) {
            if(objects[j]!=(sizes[j]==c.fail ? NULL : (void *)pool[j])) return 1;
        }
    }
    printf("PASS %s: 14 real-factory scenarios, constructor arguments, target selection, land path, allocation failure and registration\n",patched ? "patched" : "vanilla");
    return 0;
}
int wmain(int argc,wchar_t **argv) {
    if(argc!=3 || sizeof(void *)!=4) { puts("Usage (x86): test-naval-factory vanilla.dll patched.dll");return 2; }
    HMODULE original=LoadLibraryExW(argv[1],NULL,DONT_RESOLVE_DLL_REFERENCES);
    HMODULE patched=LoadLibraryExW(argv[2],NULL,DONT_RESOLVE_DLL_REFERENCES);
    if(!original || !patched || original==patched) { puts("FAIL private mappings");return 1; }
    printf("Private mappings: original=%p patched=%p (distinct load bases)\n",(void *)original,(void *)patched);
    int result=test(original,0) || test(patched,1);
    FreeLibrary(patched);FreeLibrary(original);
    if(!result) puts("PASS 28 real-factory scenarios; live naval battles remain untested");
    return result;
}
