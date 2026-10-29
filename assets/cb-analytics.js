(function(){
  var NS=(location.hostname==='callbassador.com'&&!/[?&]cbtest=1/.test(location.search))?'callbassador-com':'callbassador-test', API='https://abacus.jasoncameron.dev/hit/'+NS+'/';
  var OK={a5_price_anchor:1,a2_money:1,a1_pain:1};
  function utm(){
    var u='';
    try{var q=new URLSearchParams(location.search);u=(q.get('utm_content')||'').toLowerCase().replace(/[^a-z0-9_]/g,'');
      if(u){sessionStorage.setItem('cb_utm_content',u);}else{u=sessionStorage.getItem('cb_utm_content')||'';}}catch(e){}
    if(!u)return 'none';
    return OK[u]?u:'other';
  }
  function planSlug(p){
    p=p||'';
    if(p.indexOf('demo')!==-1||p.indexOf('thanks.html')!==-1)return 'demo';
    if(p.indexOf('$79')!==-1||p.indexOf('6oU00j4re9Mm6n4g4h1Jm03')!==-1)return 'starter79';
    if(p.indexOf('$149')!==-1||p.indexOf('8x27sL6zme2C3aS19n1Jm02')!==-1)return 'pro149';
    if(p.indexOf('$249')!==-1||p.indexOf('14AeVd7DqcYycLs05j1Jm00')!==-1)return 'crew249';
    return 'pro99';
  }
  function hit(k){
    var url=API+k.slice(0,64);
    try{ if(window.fetch){fetch(url,{method:'GET',mode:'no-cors',keepalive:true,credentials:'omit'}).catch(function(){});return;} }catch(e){}
    try{(new Image()).src=url;}catch(e){}
  }
  function ev(name,extra){ var u=utm(); hit(name+'__all'); hit(name+'__'+u); if(extra){hit(name+'__'+extra); hit(name+'__'+extra+'__'+u);} }
  window.cbTrack=ev;
  var U=utm();
  ev('visit');
  document.addEventListener('submit',function(e){
    try{var f=e.target; if(!f||!f.classList||!f.classList.contains('cb-step1-form'))return;
      var p=(f.elements['plan']&&f.elements['plan'].value)||'';
      var n=(f.elements['_next']&&f.elements['_next'].value)||'';
      var s=planSlug(p||n); ev('step1_submit',s);
      if(n.indexOf('https://buy.stripe.com/')===0)ev('checkout_redirect',planSlug(n));
    }catch(x){}
  },false);
  document.addEventListener('click',function(e){
    try{var a=e.target&&e.target.closest&&e.target.closest('a,button'); if(!a)return;
      var h=a.getAttribute('href')||'';
      if(h.indexOf('buy.stripe.com')!==-1)ev('checkout_redirect',planSlug(h));
      if(a.hasAttribute('data-talk-sami')||h==='#talk-to-sami'||h.indexOf('?talk=1')!==-1)ev('talk_to_sami_open');
    }catch(x){}
  },true);
  if(location.hash==='#talk-to-sami'||/[?&]talk=1(&|$)/.test(location.search))ev('talk_to_sami_open');
  var played=false;
  document.addEventListener('play',function(e){
    try{var t=e.target; if(!played&&t&&t.tagName==='AUDIO'&&(t.currentSrc||t.src||'').indexOf('sample')!==-1){played=true;ev('sample_audio_play');}}catch(x){}
  },true);
})();
