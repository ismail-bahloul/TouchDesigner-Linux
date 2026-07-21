#include <windows.h>
#include <stdint.h>
#define CMD "Z:\\tmp\\cuda_daemon.pipe"
#define RSP "Z:\\tmp\\cuda_daemon.rsp"
static HANDLE hC=INVALID_HANDLE_VALUE,hR=INVALID_HANDLE_VALUE;
static CRITICAL_SECTION cs;
static int cn(void){
 if(hC!=INVALID_HANDLE_VALUE)return 1;
 for(int i=0;i<30;i++){
  hC=CreateFileA(CMD,GENERIC_WRITE,0,NULL,OPEN_EXISTING,0,NULL);
  hR=CreateFileA(RSP,GENERIC_READ,0,NULL,OPEN_EXISTING,0,NULL);
  if(hC!=INVALID_HANDLE_VALUE&&hR!=INVALID_HANDLE_VALUE)return 1;
  if(hC!=INVALID_HANDLE_VALUE)CloseHandle(hC);
  if(hR!=INVALID_HANDLE_VALUE)CloseHandle(hR);
  hC=hR=INVALID_HANDLE_VALUE;Sleep(100);
 }return 0;
}
static int ma(const char*s){int r=0;while(*s>='0'&&*s<='9'){r=r*10+(*s-'0');s++;}return r;}
static unsigned long long mu(const char*s){unsigned long long r=0;while(*s>='0'&&*s<='9'){r=r*10+(*s-'0');s++;}return r;}
static int dc(const char*c,char*b,int m){
 DWORD w,r;char buf[4096];
 EnterCriticalSection(&cs);
 if(!cn()){LeaveCriticalSection(&cs);return 0;}
 int l=0;while(c[l])l++;
 if(!WriteFile(hC,c,l,&w,NULL)||!ReadFile(hR,buf,sizeof(buf)-1,&r,NULL)){LeaveCriticalSection(&cs);return 0;}
 buf[r]=0;if(b&&m){int i=0;while(buf[i]&&i<m-1){b[i]=buf[i];i++;}b[i]=0;}
 LeaveCriticalSection(&cs);return 1;
}
static int pr(const char*r){while(*r){if(r[0]=='"'&&r[1]=='r'&&r[2]=='e'&&r[3]=='s'&&r[4]=='u'&&r[5]=='l'&&r[6]=='t'&&r[7]=='"'&&r[8]==':')return ma(r+9);r++;}return -1;}
static void sc(char*d,const char*s){while(*d)d++;while(*s){*d=*s;d++;s++;}*d=0;}
static void su(char*d,unsigned long long v){char b[32];int i=31;b[i]=0;if(!v){b[--i]='0';}while(v){b[--i]='0'+(v%10);v/=10;}int j=0;while(b[i]){d[j++]=b[i++];}d[j]=0;}
int WINAPI cuInit(unsigned f){char cmd[64]="{\"cmd\":\"cuInit\",\"args\":[";su(cmd+19,f);sc(cmd,"]}");char b[256];return dc(cmd,b,sizeof(b))?pr(b):1;}
int WINAPI cuDeviceGetCount(int*c){char b[512];if(!dc("{\"cmd\":\"cuDeviceGetCount\"}",b,sizeof(b)))return 1;char*p=b;while(*p){if(p[0]=='"'&&p[1]=='c'&&p[2]=='o'&&p[3]=='u'&&p[4]=='n'&&p[5]=='t'&&p[6]=='"'&&p[7]==':'){if(c)*c=ma(p+8);break;}p++;}return pr(b);}
int WINAPI cuDeviceGet(int*d,int o){if(d)*d=o;return 0;}
int WINAPI cuDeviceGetName(char*n,int l,int d){char cmd[128]="{\"cmd\":\"cuDeviceGetName\",\"args\":[";su(cmd+32,d);sc(cmd,"]}");char b[1024];if(!dc(cmd,b,sizeof(b)))return 1;char*p=b;while(*p){if(p[0]=='"'&&p[1]=='n'&&p[2]=='a'&&p[3]=='m'&&p[4]=='e'&&p[5]=='"'&&p[6]==':'){p+=8;int i=0;while(*p&&*p!='"'&&i<l-1){if(*p!='\\')n[i++]=*p;p++;}n[i]=0;break;}p++;}return pr(b);}
int WINAPI cuCtxCreate(void**p,unsigned f,int d){char cmd[128]="{\"cmd\":\"cuCtxCreate\",\"args\":[0,";su(cmd+30,d);sc(cmd,"]}");char b[1024];if(!dc(cmd,b,sizeof(b)))return 1;char*s=b;while(*s){if(s[0]=='"'&&s[1]=='c'&&s[2]=='t'&&s[3]=='x'&&s[4]=='"'&&s[5]==':'){if(p)*p=(void*)(uintptr_t)mu(s+6);break;}s++;}return pr(b);}
int WINAPI cuMemAlloc(uint64_t*p,size_t s){char cmd[128]="{\"cmd\":\"cuMemAlloc\",\"args\":[";su(cmd+24,s);sc(cmd,"]}");char b[1024];if(!dc(cmd,b,sizeof(b)))return 1;char*x=b;while(*x){if(x[0]=='"'&&x[1]=='p'&&x[2]=='t'&&x[3]=='r'&&x[4]=='"'&&x[5]==':'){if(p)*p=mu(x+6);break;}x++;}return pr(b);}
int WINAPI cuMemFree(uint64_t p){char cmd[128]="{\"cmd\":\"cuMemFree\",\"args\":[";su(cmd+23,p);sc(cmd,"]}");char b[256];return dc(cmd,b,sizeof(b))?pr(b):1;}
int WINAPI cudaGetDeviceCount(int*c){return cuDeviceGetCount(c);}
int WINAPI cudaSetDevice(int d){void*c;return cuCtxCreate(&c,0,d);}
int WINAPI cudaMalloc(void**p,size_t s){uint64_t x;int r=cuMemAlloc(&x,s);if(p)*p=(void*)(uintptr_t)x;return r;}
int WINAPI cudaFree(void*p){return cuMemFree((uint64_t)(uintptr_t)p);}
int WINAPI cudaMemcpy(void*d,const void*s,size_t n,int k){return 0;}
int WINAPI cudaGetDeviceProperties(void*prop,int dev){
 char*name=(char*)prop;if(!name)return 1;
 for(int i=0;i<256;i++)name[i]=0;
 char cmd[128]="{\"cmd\":\"cuDeviceGetName\",\"args\":[";su(cmd+32,dev);sc(cmd,"]}");
 char b[1024];if(dc(cmd,b,sizeof(b))){
  char*x=b;while(*x){if(x[0]=='"'&&x[1]=='n'&&x[2]=='a'&&x[3]=='m'&&x[4]=='e'&&x[5]=='"'&&x[6]==':'){x+=8;int i=0;while(*x&&*x!='"'&&i<255){if(*x!='\\')name[i++]=*x;x++;}name[i]=0;break;}x++;}
 }else sc(name,"NVIDIA GPU (Wine)");
 *(int*)((char*)prop+260)=8;*(int*)((char*)prop+264)=9;return 0;
}
int WINAPI cudaRuntimeGetVersion(int*v){if(v)*v=12090;return 0;}
const char*WINAPI cudaGetErrorString(int e){return "CUDA error (Wine)";}
int WINAPI __cudaRegisterFatBinary(void*f){return (int)(uintptr_t)f;}
int WINAPI __cudaRegisterFunction(void**f,const char*s,void*func,int t,const char*d){return 0;}
int WINAPI __cudaUnregisterFatBinary(int h){return 0;}
int WINAPI __cudaPushCallConfiguration(int gx,int gy,int gz,int bx,int by,int bz,size_t sm,void*st){return 0;}
int WINAPI __cudaPopCallConfiguration(int*gx,int*gy,int*gz,int*bx,int*by,int*bz,size_t*sm,void**st){
 if(gx)*gx=1;if(gy)*gy=1;if(gz)*gz=1;if(bx)*bx=256;if(by)*by=1;if(bz)*bz=1;if(sm)*sm=0;if(st)*st=0;return 0;}
int WINAPI cudaCreateSurfaceObject(void**s,const void*d){if(s)*s=(void*)1;return 0;}
int WINAPI cudaDestroySurfaceObject(void*s){return 0;}
int WINAPI cudaCreateTextureObject(void**t,const void*d,const void*td,const void*r){if(t)*t=(void*)1;return 0;}
int WINAPI cudaDestroyTextureObject(void*t){return 0;}
int WINAPI cudaGetSurfaceObjectResourceDesc(void*d,void*s){memset(d,0,48);return 0;}
int WINAPI cudaGetTextureObjectResourceDesc(void*d,void*t){memset(d,0,48);return 0;}
int WINAPI cudaStreamCreate(void**p,unsigned f){if(p)*p=(void*)1;return 0;}
int WINAPI cudaEventCreate(void**p,unsigned f){if(p)*p=(void*)1;return 0;}
int WINAPI cudaEventRecord(void*e,void*s){return 0;}
int WINAPI cudaEventSynchronize(void*e){return 0;}
int WINAPI cudaLaunchKernel(const void*s,int gx,int gy,int gz,int bx,int by,int bz,size_t sm,void*st,void**a,void**e){return 0;}
int WINAPI cudaConfigureCall(int gx,int gy,int gz,int bx,int by,int bz,size_t sm,void*st){return 0;}
int WINAPI cudaLaunch(const char*s){return 0;}
int WINAPI cudaMallocHost(void**p,size_t s){*p=VirtualAlloc(NULL,s,MEM_COMMIT,PAGE_READWRITE);return*p?0:1;}
int WINAPI cudaFreeHost(void*p){VirtualFree(p,0,MEM_RELEASE);return 0;}
BOOL WINAPI DllMain(HINSTANCE h,DWORD r,LPVOID l){
 if(r==DLL_PROCESS_ATTACH){DisableThreadLibraryCalls(h);InitializeCriticalSection(&cs);cn();}
 return TRUE;
}
