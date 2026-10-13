// A transição troca a tela sem esperar pelos dados nem atrasar os controles.
(()=>{
 const navigate=go;
 let activeTransition=null,sequence=0;
 go=function(target){
  const request=++sequence;
  activeTransition?.skipTransition();
  const reduced=window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
  if(!ready||target===view||reduced||!document.startViewTransition){
   activeTransition=null;
   document.documentElement?.classList.remove('motion-navigating');
   return navigate(target);
  }
  let navigationTask;
  const root=document.documentElement;
  root.classList.add('motion-navigating');
  let transition;
  try{
   transition=document.startViewTransition(()=>{
    if(request!==sequence)return;
    navigationTask=navigate(target);
   });
  }catch{
   root.classList.remove('motion-navigating');
   return navigate(target);
  }
  activeTransition=transition;
  transition.ready.catch(()=>{});
  transition.finished.catch(()=>{}).finally(()=>{
   if(activeTransition===transition){
    root.classList.remove('motion-navigating');
    activeTransition=null;
   }
  });
  return transition.updateCallbackDone.then(()=>navigationTask);
 };
})();
