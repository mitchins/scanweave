/* Read-only public Win32 control inspection of the normal OCR settings dialog.
 * No executable inspection, process-memory access, or Adobe resource copying.
 * Built without an SDK using import libraries for documented Windows APIs. */
typedef void *HWND; typedef void *HANDLE;
typedef unsigned long DWORD; typedef unsigned int UINT; typedef unsigned long WPARAM;
typedef long LPARAM; typedef long LRESULT; typedef int BOOL;
#define API __declspec(dllimport)
API HWND __stdcall FindWindowA(const char *,const char *);
API BOOL __stdcall EnumChildWindows(HWND,BOOL (__stdcall *)(HWND,LPARAM),LPARAM);
API int __stdcall GetClassNameA(HWND,char *,int);
API LRESULT __stdcall SendMessageA(HWND,UINT,WPARAM,LPARAM);
API LRESULT __stdcall SendMessageW(HWND,UINT,WPARAM,LPARAM);
API HANDLE __stdcall GetStdHandle(DWORD);
API BOOL __stdcall WriteFile(HANDLE,const void *,DWORD,DWORD *,void *);
API void __stdcall ExitProcess(UINT);
void *memset(void *p,int v,unsigned n){unsigned char *q=p;for(unsigned i=0;i<n;i++)q[i]=(unsigned char)v;return p;}
static unsigned len(const char *s){unsigned n=0;while(s[n])n++;return n;}
static void print(const char *s){DWORD n;WriteFile(GetStdHandle((DWORD)-11),s,len(s),&n,0);}
static void wide(const unsigned short *s){char t[2048];unsigned n=0;for(unsigned i=0;s[i] && i<511;i++){unsigned c=s[i];if(c<128)t[n++]=(char)c;else if(c<2048){t[n++]=(char)(192|(c>>6));t[n++]=(char)(128|(c&63));}else{t[n++]=(char)(224|(c>>12));t[n++]=(char)(128|((c>>6)&63));t[n++]=(char)(128|(c&63));}}t[n]=0;print(t);}
static BOOL __stdcall child(HWND h,LPARAM unused){
    char cls[128]={0},text[512]={0};(void)unused;
    GetClassNameA(h,cls,127);if(len(cls)==8 && cls[0]=='C' && cls[1]=='o')return 1;SendMessageA(h,0x000D,511,(LPARAM)text);
    print(cls);print(": ");print(text);print("\r\n");
    if(cls[0]=='C' && cls[1]=='o' && cls[2]=='m' && cls[8]=='E'){
        LRESULT selected=SendMessageA(h,0x0147,0,0);
        if(selected>=0){unsigned short selected_text[512]={0};SendMessageW(h,0x0148,(WPARAM)selected,(LPARAM)selected_text);print("SELECTED: ");wide(selected_text);print("\r\n");}
    }
    return 1;
}
void main(void){HWND h=FindWindowA(0,"Recognize Text - General Settings");if(!h){print("OCR settings dialog not open\r\n");ExitProcess(1);}EnumChildWindows(h,child,0);ExitProcess(0);}
