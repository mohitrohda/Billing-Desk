const BASE = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';
export function getToken(){ return localStorage.getItem('billing_token'); }
export async function apiRequest(path, options={}){
  const headers={...(options.body ? {'Content-Type':'application/json'} : {}), ...(getToken()?{Authorization:`Bearer ${getToken()}`} : {}), ...(options.headers||{})};
  const response=await fetch(`${BASE}${path}`,{...options,headers});
  if(!response.ok){ let message=`Request failed (${response.status})`; try{const body=await response.json(); message=typeof body.detail==='string'?body.detail:Array.isArray(body.detail)?body.detail.map(item=>item.msg||JSON.stringify(item)).join('; '):body.message||message;}catch{} throw new Error(message); }
  if(response.status===204) return null;
  const type=response.headers.get('content-type')||'';
  return type.includes('application/pdf') ? response.blob() : response.json();
}
export async function downloadInvoice(id){
  const blob=await apiRequest(`/api/invoices/${id}/pdf`); const url=URL.createObjectURL(blob); const a=document.createElement('a'); a.href=url; a.download=`invoice-${id}.pdf`; a.click(); URL.revokeObjectURL(url);
}
