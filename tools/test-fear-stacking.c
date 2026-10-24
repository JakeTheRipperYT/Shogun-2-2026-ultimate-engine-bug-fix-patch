// Private mappings only: execute real constructor fragment and complete fear receiver.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <limits.h>
static BYTE kv[0x2300],own[0x1000],morale[0x80],manager0[0x20],manager1[0xc0],manager2[0x400];
static BYTE enemies[8][0x1000];
static int enemyCount,ownHorse,emittedId[4],emittedValue[4],emittedCount,fail;
static void *entry;
static void * __fastcall database(void *,void *) {return kv;}
static int __fastcall eligible(void *unit,void *) {return *(int *)((BYTE *)unit+0x100);}
static int __fastcall horse(void *,void *) {return ownHorse;}
static void __fastcall query(void *,void *,void *output,void *source,float range,int mode) {
    if(source!=own || range!=40.0f || mode!=1){fail=1;return;}
    for(int i=0;i<enemyCount;++i)((void **)output)[i]=enemies[i];
    *(int *)((BYTE *)output+0x2800)=enemyCount;
}
static void __fastcall emit(void *self,void *,int id,int value) {
    if(self!=morale || emittedCount>=4){fail=1;return;}
    emittedId[emittedCount]=id;emittedValue[emittedCount++]=value;
}
static void patch(BYTE *at,void *target) {
    DWORD previous=0;VirtualProtect(at,5,PAGE_EXECUTE_READWRITE,&previous);
    at[0]=0xe9;*(DWORD *)(at+1)=(DWORD)target-(DWORD)at-5;
    DWORD ignored=0;VirtualProtect(at,5,previous,&ignored);FlushInstructionCache(GetCurrentProcess(),at,5);
}
// Entry is a mid-constructor block, supplied the original stack slot/register contract.
static __declspec(naked) int __cdecl construct(int,int) {
    __asm {
        push ebp
        push ebx
        push esi
        push edi
        mov edx,[esp+20]
        mov ecx,[esp+24]
        sub esp,0xb0
        mov [esp+0x9c],ecx
        mov eax,offset finished
        mov [esp],eax
        mov esi,0x12345678
        mov eax,edx
        jmp dword ptr [entry]
    finished:
        mov eax,[esp+0x98]
        sub esp,4
        add esp,0xb0
        pop edi
        pop esi
        pop ebx
        pop ebp
        ret
    }
}
static int constructorTests(BYTE *base,int candidate) {
    entry=base+0x152b23;
    patch(base+0xbd1660,(void *)database);
    BYTE *end=base+0x152b44;DWORD old=0;VirtualProtect(end,1,PAGE_EXECUTE_READWRITE,&old);*end=0xc3;
    DWORD ignored=0;VirtualProtect(end,1,old,&ignored);FlushInstructionCache(GetCurrentProcess(),end,1);
    int cases=0;
    for(int innate=0;innate<=4;innate+=4)
    for(int trait=0;trait<=3;++trait)
    for(int sword=0;sword<=1;++sword)
    for(int skill=0;skill<=2;++skill)
    for(int mask=0;mask<=1;++mask) {
        int oldBonus=-trait-sword-mask+(skill?1:0);
        int newBonus=-trait-sword-mask-(skill?4:0);
        int bonus=candidate?newBonus:oldBonus;
        int expected=candidate?innate-newBonus:(oldBonus?4:innate);
        int actual=construct(bonus,innate);
        if(actual!=expected){printf("FAIL constructor candidate=%d trait=%d sword=%d skill=%d mask=%d innate=%d aggregate=%d got=%d expected=%d\n",candidate,trait,sword,skill,mask,innate,bonus,actual,expected);return 1;}
        ++cases;
    }
    const int extras[]={0,1,2,4,8,INT_MAX,-1,-2,-3,-4,-8,-INT_MAX,INT_MIN};
    for(unsigned i=0;i<sizeof(extras)/sizeof(extras[0]);++i)
    for(int innate=0;innate<=4;innate+=4) {
        int bonus=extras[i];__int64 n=bonus;
        if(n<0)n=-n;n+=innate;
        int numeric=n>INT_MAX?INT_MAX:(int)n;
        int expected=bonus==0?innate:((candidate&&bonus<0)?numeric:4);
        int actual=construct(bonus,innate);
        if(actual!=expected){printf("FAIL edge candidate=%d bonus=%d innate=%d got=%d expected=%d\n",candidate,bonus,innate,actual,expected);return 1;}
        ++cases;
    }
    printf("PASS %s constructor: %d real-code source combinations/zero/legacy-positive/innate/overflow cases\n",candidate?"candidate":"vanilla",cases);
    return 0;
}
static int receiverTests(BYTE *base) {
    patch(base+0x48d860,(void *)query);patch(base+0x182620,(void *)eligible);
    patch(base+0x1804a0,(void *)horse);patch(base+0x16f780,(void *)emit);
    typedef void (__thiscall *Aura)(void *);
    Aura aura=(Aura)(base+0x158100);
    const int strengths[]={0,1,2,3,4,6,8,INT_MAX};int cases=0;
    for(unsigned a=0;a<sizeof(strengths)/sizeof(strengths[0]);++a)
    for(unsigned b=0;b<sizeof(strengths)/sizeof(strengths[0]);++b)
    for(int valid=0;valid<=1;++valid)
    for(int horses=0;horses<=1;++horses) {
        memset(enemies,0,sizeof(enemies));enemyCount=2;ownHorse=horses;emittedCount=0;fail=0;
        *(int *)(enemies[0]+0x154)=strengths[a];*(int *)(enemies[1]+0x154)=strengths[b];
        *(int *)(enemies[0]+0x100)=1;*(int *)(enemies[1]+0x100)=valid;
        enemies[1][0x153]=1;
        aura(morale);
        int maximum=strengths[a];if(valid&&strengths[b]>maximum)maximum=strengths[b];
        int expectedCount=(maximum>0?1:0)+(valid&&horses?1:0),index=0;
        if(fail || emittedCount!=expectedCount){printf("FAIL aura count got=%d expected=%d\n",emittedCount,expectedCount);return 1;}
        if(maximum>0){if(emittedId[index]!=0x2d||emittedValue[index]!=-maximum){puts("FAIL strongest fear magnitude");return 1;}++index;}
        if(valid&&horses){if(emittedId[index]!=0x2c||emittedValue[index]!=-4){puts("FAIL horse fear isolation");return 1;}}
        ++cases;
    }
    printf("PASS receiver: %d complete native aura cases; maximum positive strength, eligibility, range and horse fear preserved\n",cases);return 0;
}
int wmain(int argc,wchar_t **argv) {
    setvbuf(stdout,NULL,_IONBF,0);if(argc!=3||sizeof(void *)!=4){puts("Usage (x86): test-fear-stacking vanilla.dll candidate.dll");return 2;}
    HMODULE vanilla=LoadLibraryExW(argv[1],NULL,DONT_RESOLVE_DLL_REFERENCES),candidate=LoadLibraryExW(argv[2],NULL,DONT_RESOLVE_DLL_REFERENCES);
    if(!vanilla||!candidate||vanilla==candidate){puts("FAIL distinct private mappings");return 2;}
    printf("Private ASLR mappings vanilla=%p candidate=%p\n",vanilla,candidate);
    *(int *)(kv+0x1988)=-4;*(int *)(kv+0x19e8)=-4;*(int *)(kv+0x968)=40;
    *(void **)(morale+0x6c)=kv;*(void **)(morale+4)=own;*(void **)morale=manager0;
    *(void **)(manager0+8)=manager1;*(void **)(manager1+0xb4)=manager2;
    int failed=constructorTests((BYTE *)vanilla,0)||constructorTests((BYTE *)candidate,1)||receiverTests((BYTE *)vanilla)||receiverTests((BYTE *)candidate);
    FreeLibrary(candidate);FreeLibrary(vanilla);return failed;
}
