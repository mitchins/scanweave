#include <stdint.h>
#include <stdlib.h>
#include <stddef.h>
/* Unit-cost Levenshtein; U+FFFD in the reference matches one hypothesis code point. */
int books01_edit(const uint32_t *a, size_t n, const uint32_t *b, size_t m) {
 int *old=malloc((m+1)*sizeof(int)), *cur=malloc((m+1)*sizeof(int)); if(!old||!cur){free(old);free(cur);return -1;}
 for(size_t j=0;j<=m;j++)old[j]=(int)j;
 for(size_t i=1;i<=n;i++){cur[0]=(int)i; for(size_t j=1;j<=m;j++){int x=old[j]+1,y=cur[j-1]+1,z=old[j-1]+(a[i-1]!=0xfffd&&a[i-1]!=b[j-1]);int t=x<y?x:y;cur[j]=t<z?t:z;}int *t=old;old=cur;cur=t;}
 int result=old[m];free(old);free(cur);return result;
}
