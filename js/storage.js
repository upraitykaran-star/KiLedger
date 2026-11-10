const KEY='kileger-frontend-v1';
const empty=()=>({users:[],businesses:[],customers:[],products:[],suppliers:[],orders:[],transactions:[],payments:[],returns:[],activity:[],sessions:{}});
export function readDB(){try{const raw=localStorage.getItem(KEY);return raw?{...empty(),...JSON.parse(raw)}:empty()}catch(error){console.error('KiLedger storage read failed',error);throw new Error('KiLedger could not read this browser’s saved data. Check available storage and try again.')}}
export function writeDB(db){try{localStorage.setItem(KEY,JSON.stringify(db))}catch(error){console.error('KiLedger storage write failed',error);throw new Error('KiLedger could not save your change. Browser storage may be full or unavailable.')}}
export function updateDB(updater){const db=readDB();const next=updater(db)||db;writeDB(next);return next}
export function id(prefix='ID'){return `${prefix}-${Date.now().toString(36).toUpperCase()}-${crypto.getRandomValues(new Uint32Array(1))[0].toString(36).toUpperCase()}`}
export const currentSession=()=>{try{return JSON.parse(sessionStorage.getItem('kileger-session-v1')||'null')}catch{return null}};
export function setSession(userId,businessId,mode){sessionStorage.setItem('kileger-session-v1',JSON.stringify({userId,businessId,mode:mode||null}))}
export function clearSession(){sessionStorage.removeItem('kileger-session-v1')}
export const money=value=>new Intl.NumberFormat('en-IN',{style:'currency',currency:'INR',maximumFractionDigits:2}).format(Number(value)||0);
export const dateLabel=value=>value?new Date(`${value}T00:00:00`).toLocaleDateString('en-IN',{day:'numeric',month:'short',year:'numeric'}):'—';
export const ownRecords=(db,key,businessId)=>db[key].filter(row=>row.businessId===businessId);
export function addActivity(db,businessId,text){db.activity.unshift({id:id('ACT'),businessId,text,date:new Date().toISOString()});db.activity=db.activity.slice(0,80)}
export function generateReference(db,key,businessId,prefix){let counter=1,ref='';do{ref=`${prefix}-${String(counter++).padStart(4,'0')}`}while(db[key].some(item=>item.businessId===businessId&&item.reference===ref));return ref}
