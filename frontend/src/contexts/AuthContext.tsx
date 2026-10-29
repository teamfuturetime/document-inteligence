import {createContext,useContext,useEffect,useState,type ReactNode} from 'react';import {api} from '../api/client';import type{User}from'../types';
import {clearOCRDrafts,hasOCRDrafts,syncOCRDraftAccount} from '../utils/ocrDrafts'
type Auth={user:User|null;loading:boolean;login:(a:string,b:string)=>Promise<void>;register:(a:string,b:string,c:string)=>Promise<void>;logout:()=>Promise<void>};const Context=createContext<Auth>(null!);
export function AuthProvider({children}:{children:ReactNode}){
 const[user,setUser]=useState<User|null>(null);const[loading,setLoading]=useState(true)
 function signedIn(value:User){syncOCRDraftAccount(value.id);setUser(value)}
 useEffect(()=>{api.me().then(signedIn).catch(()=>setUser(null)).finally(()=>setLoading(false))},[])
 return <Context.Provider value={{user,loading,login:async(a,b)=>signedIn(await api.login(a,b)),register:async(a,b,c)=>signedIn(await api.register(a,b,c)),logout:async()=>{
  if(hasOCRDrafts()&&!window.confirm('Bạn có bản nháp OCR chưa lưu. Đăng xuất sẽ xóa các bản nháp trong tab này. Bạn muốn tiếp tục?'))return
  await api.logout();clearOCRDrafts();setUser(null)
 }}}>{children}</Context.Provider>
};export const useAuth=()=>useContext(Context)
