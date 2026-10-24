// Actual x86/Windows private mappings, not Unicorn. Patch only the private IAT
// slot to a recording stdcall fixture. No live game or on-disk DLL is changed.
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#include <stdio.h>
#include <string.h>
#include <wchar.h>
typedef HANDLE (__stdcall *Open7)(LPCWSTR,DWORD,DWORD,LPSECURITY_ATTRIBUTES,DWORD,DWORD,HANDLE);
struct Arguments {LPCWSTR path;DWORD access,share;LPSECURITY_ATTRIBUTES security;DWORD disposition,flags;HANDLE parent;};
static Arguments captured;
static WCHAR capturedPath[1024];
static int calls;
static HANDLE __stdcall openFixture(LPCWSTR path,DWORD access,DWORD share,LPSECURITY_ATTRIBUTES security,DWORD disposition,DWORD flags,HANDLE parent) {
    captured.path=path;captured.access=access;captured.share=share;captured.security=security;
    captured.disposition=disposition;captured.flags=flags;captured.parent=parent;++calls;
    if(path) wcscpy_s(capturedPath,sizeof(capturedPath)/sizeof(capturedPath[0]),path);
    else capturedPath[0]=0;
    return (HANDLE)0x12345678;
}
// out = beforeESP,afterESP,EBX,ESI,EDI,result. Explicit stack frame survives the
// candidate changing EAX/ECX/EDX; recovery lets a stack mismatch report cleanly.
static __declspec(naked) HANDLE __cdecl invoke(Open7,Arguments *,DWORD *) {
    __asm {
        push ebp
        mov ebp,esp
        push ebx
        push esi
        push edi
        mov edx,[ebp+16]
        mov [edx],esp
        mov eax,[ebp+12]
        push [eax+24]
        push [eax+20]
        push [eax+16]
        push [eax+12]
        push [eax+8]
        push [eax+4]
        push [eax]
        mov ebx,0B0B0B0B0h
        mov esi,051515151h
        mov edi,0D1D1D1D1h
        call dword ptr [ebp+8]
        mov edx,[ebp+16]
        mov [edx+4],esp
        mov [edx+8],ebx
        mov [edx+12],esi
        mov [edx+16],edi
        mov [edx+20],eax
        lea esp,[ebp-12]
        pop edi
        pop esi
        pop ebx
        pop ebp
        ret
    }
}
static __declspec(naked) DWORD __cdecl loaderResult(void *) {
    __asm {
        push ebx
        call dword ptr [esp+8]
        mov eax,ebx
        pop ebx
        ret
    }
}
static int run(HMODULE module,int patched) {
    BYTE *base=(BYTE *)module;
    void **iat=(void **)(base+0x15A1144),*saved=*iat;DWORD protection=0;
    if(!VirtualProtect(iat,4,PAGE_READWRITE,&protection)) return 1;
    *iat=(void *)openFixture;
    Open7 entry=patched ? (Open7)(base+0x15A0C4A) : (Open7)*iat;
    const WCHAR *paths[]={NULL,L"",L"data.pack",L"data\\data.pack",L"DATA/DATA.PACK",L"C:\\Games\\SHOGUN 2\\data\\data.pack",
        L"C:/Games/\x5c06\x8ecd/data/DATA.PACK",L"data\\models.pack",L"data\\local_en.pack",L"data\\boot.pack",
        L"C:\\Games\\data\\models.pack",L"C:\\Games\\data\\local_en.pack",L"mydata\\data.pack",L"data\\xdata.pack",L"data\\data.pack.bak"};
    const DWORD accesses[]={0,1,0x80000000,0xC0000000,0x10000000,2,4,0x10,0x40,0x100,0x10000,0x40000,0x80000,0x01000000,0x02000000};
    int cases=0;
    for(unsigned p=0;p<sizeof(paths)/sizeof(paths[0]);++p)
    for(unsigned a=0;a<sizeof(accesses)/sizeof(accesses[0]);++a)
    for(DWORD disposition=1;disposition<=5;++disposition) {
        Arguments args={paths[p],accesses[a],0x1122,(LPSECURITY_ATTRIBUTES)0x33445566,disposition,0x02000080,(HANDLE)0x55667788};
        DWORD result[6]={0};calls=0;HANDLE returned=invoke(entry,&args,result);
        bool matches=p==3 || p==4 || p==5 || p==6;
        const WCHAR *expected=patched && matches && disposition==3 && !(args.access&0x530D0156) ? L"UltimatePatch\\data\\data.pack" : paths[p];
        bool pathOK=expected ? captured.path && wcscmp(capturedPath,expected)==0 : captured.path==NULL;
        if(!pathOK || calls!=1 || returned!=(HANDLE)0x12345678 || result[5]!=0x12345678 || result[0]!=result[1] ||
           result[2]!=0xB0B0B0B0 || result[3]!=0x51515151 || result[4]!=0xD1D1D1D1 ||
           captured.access!=args.access || captured.share!=args.share || captured.security!=args.security ||
           captured.disposition!=args.disposition || captured.flags!=args.flags || captured.parent!=args.parent) {
            printf("FAIL %s path=%u access=%08lX disposition=%lu\n",patched ? "redirect" : "baseline",p,args.access,disposition);return 1;
        }
        ++cases;
    }
    if(patched && loaderResult(base+0x15A0C40)!=(DWORD)(base+0x15A0C4A)) {puts("FAIL EBX loader");return 1;}
    *iat=saved;DWORD ignored=0;VirtualProtect(iat,4,protection,&ignored);
    printf("PASS %s: %d real-code cases, Win32 arguments/return, ESP and EBX/ESI/EDI preserved%s\n",
        patched ? "redirect" : "baseline",cases,patched ? "; PIC EBX loader verified" : "");
    return 0;
}
int wmain(int argc,wchar_t **argv) {
    setvbuf(stdout,NULL,_IONBF,0);
    if(argc!=3 || sizeof(void *)!=4) {puts("Usage (x86): test-data-pack-redirect vanilla.dll patched.dll");return 2;}
    HMODULE original=LoadLibraryExW(argv[1],NULL,DONT_RESOLVE_DLL_REFERENCES);
    HMODULE patched=LoadLibraryExW(argv[2],NULL,DONT_RESOLVE_DLL_REFERENCES);
    if(!original || !patched || original==patched) {puts("FAIL distinct native mappings");return 2;}
    printf("Native ASLR mappings: vanilla=%p patched=%p\n",original,patched);
    int failed=run(original,0) || run(patched,1);
    FreeLibrary(patched);FreeLibrary(original);return failed;
}
