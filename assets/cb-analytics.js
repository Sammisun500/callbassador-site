(function(){
  var NS=(location.hostname==='callbassador.com'&&!/[?&]cbtest=1/.test(location.search))?'callbassador-com':'callbassador-test', API='https://abacus.jasoncameron.dev/hit/'+NS+'/';
  // Oct 31 2026: test mode (cbtest=1 in URL, or remembered in sessionStorage for the tab) skips ALL counting.
  var TEST=/[?&]cbtest=1(&|$)/.test(location.search);
  try{ if(TEST){sessionStorage.setItem('cb_test','1');}else if(sessionStorage.getItem('cb_test')==='1'){TEST=true;} }catch(e){}
  function day(){
    try{var p=new Intl.DateTimeFormat('en-US',{timeZone:'America/New_York',month:'2-digit',day:'2-digit'}).formatToParts(new Date()),m='',d='';
      for(var i=0;i<p.length;i++){if(p[i].type==='month')m=p[i].value;if(p[i].type==='day')d=p[i].value;}
      if(m&&d)return m+d;}catch(e){}
    return '';
  }
  var DAY=day();
  var OK={a5_price_anchor:1,a2_money:1,a1_pain:1};
  var UTM_KEYS=['utm_source','utm_medium','utm_campaign','utm_content','utm_term'];
  function captureUtms(){
    var out={};
    try{
      var q=new URLSearchParams(location.search);
      var found=false;
      for(var i=0;i<UTM_KEYS.length;i++){
        var k=UTM_KEYS[i], v=(q.get(k)||'').trim();
        if(v){out[k]=v.slice(0,80); found=true;}
      }
      if(found){
        try{sessionStorage.setItem('cb_utm_params',JSON.stringify(out));}catch(e){}
      }else{
        try{out=JSON.parse(sessionStorage.getItem('cb_utm_params')||'{}')||{};}catch(e){out={};}
      }
    }catch(e){out={};}
    return out;
  }
  var UTM_PARAMS=captureUtms();
  function utm(){
    var u='';
    try{
      u=((UTM_PARAMS.utm_content||'')||'').toLowerCase().replace(/[^a-z0-9_]/g,'');
      if(!u){
        var q=new URLSearchParams(location.search);u=(q.get('utm_content')||'').toLowerCase().replace(/[^a-z0-9_]/g,'');
        if(u){sessionStorage.setItem('cb_utm_content',u);}else{u=sessionStorage.getItem('cb_utm_content')||'';}
      }else{
        try{sessionStorage.setItem('cb_utm_content',u);}catch(e){}
      }
    }catch(e){}
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
  function hit1(k){
    var url=API+k.slice(0,64);
    try{ if(window.fetch){fetch(url,{method:'GET',mode:'no-cors',keepalive:true,credentials:'omit'}).catch(function(){});return;} }catch(e){}
    try{(new Image()).src=url;}catch(e){}
  }
  // Every event also counts a dated copy (key__MMDD, America/New_York) for daily numbers.
  function hit(k){ if(TEST)return; hit1(k); if(DAY)hit1(k.slice(0,58)+'__'+DAY); }
  function ev(name,extra){ var u=utm(); hit(name+'__'+(extra?extra+'__':'')+u); }
  window.cbTrack=ev;
  function meta(eventName, params, custom){
    try{
      if(typeof window.fbq!=='function')return;
      if(custom){ window.fbq('trackCustom', eventName, params||{}); }
      else{ window.fbq('track', eventName, params||{}); }
    }catch(e){}
  }
  function appendStripeAttribution(url){
    try{
      if(!url||url.indexOf('buy.stripe.com')===-1)return url;
      var u=new URL(url);
      var params=UTM_PARAMS||{};
      for(var i=0;i<UTM_KEYS.length;i++){
        var k=UTM_KEYS[i];
        if(params[k]&&!u.searchParams.get(k))u.searchParams.set(k,params[k]);
      }
      if(!u.searchParams.get('client_reference_id')){
        var parts=[];
        for(var j=0;j<UTM_KEYS.length;j++){
          var kk=UTM_KEYS[j];
          if(params[kk])parts.push(kk.replace('utm_','')+'='+String(params[kk]).slice(0,24));
        }
        if(parts.length){
          var ref=parts.join('|').slice(0,200);
          u.searchParams.set('client_reference_id',ref);
        }
      }
      return u.toString();
    }catch(e){ return url; }
  }
  window.cbAppendStripeAttribution=appendStripeAttribution;
  var U=utm();
  ev('visit');
  if(/(^|\/)thanks\.html$/.test(location.pathname)||/(^|\/)thanks\/?$/.test(location.pathname))ev('thanks');
  // First focus/input on the Step 1 form, once per page load.
  var started=false;
  function st(e){ try{ if(started)return; var f=e.target&&e.target.closest&&e.target.closest('form.cb-step1-form'); if(!f)return; started=true; ev('step1_start'); }catch(x){} }
  document.addEventListener('focusin',st,true);
  document.addEventListener('input',st,true);
  document.addEventListener('submit',function(e){
    try{var f=e.target; if(!f||!f.classList||!f.classList.contains('cb-step1-form'))return;
      var p=(f.elements['plan']&&f.elements['plan'].value)||'';
      var n=(f.elements['_next']&&f.elements['_next'].value)||'';
      var s=planSlug(p||n); ev('step1_submit',s);
      if(n.indexOf('https://buy.stripe.com/')===0){
        ev('checkout_redirect',planSlug(n));
        meta('InitiateCheckout',{content_name:s,currency:'USD',value:0});
      }else{
        // Demo-only path still counts as starting checkout intent for Meta
        meta('InitiateCheckout',{content_name:s||'demo',currency:'USD',value:0});
      }
    }catch(x){}
  },false);
  document.addEventListener('click',function(e){
    try{
      var t=e.target;
      // "Chat with Sami" Retell FAB / widget root
      if(t&&t.closest&&(t.closest('#retell-widget-root')||t.closest('[data-fab-text]')||t.closest('#retell-widget'))){
        ev('chat_with_sami_click');
        meta('Contact',{content_name:'Chat with Sami'});
      }
      var a=t&&t.closest&&t.closest('a,button'); if(!a)return;
      var h=a.getAttribute('href')||'';
      if(h.indexOf('buy.stripe.com')!==-1){
        ev('checkout_redirect',planSlug(h));
        meta('InitiateCheckout',{content_name:planSlug(h),currency:'USD',value:0});
        var attributed=appendStripeAttribution(h);
        if(attributed!==h){ a.setAttribute('href',attributed); }
      }
      if(h.indexOf('tel:')===0)ev('call_link_tap');
      if(a.hasAttribute('data-talk-sami')||h==='#talk-to-sami'||h.indexOf('?talk=1')!==-1){
        ev('talk_to_sami_open');
        meta('Contact',{content_name:'Talk to Sami voice demo'});
      }
    }catch(x){}
  },true);
  if(location.hash==='#talk-to-sami'||/[?&]talk=1(&|$)/.test(location.search)){
    ev('talk_to_sami_open');
    meta('Contact',{content_name:'Talk to Sami voice demo'});
  }
  var played=false;
  document.addEventListener('play',function(e){
    try{var t=e.target; if(!played&&t&&t.tagName==='AUDIO'&&(t.currentSrc||t.src||'').indexOf('sample')!==-1){
      played=true;
      var tag=(t.getAttribute('data-sample-tag')||'other').replace(/[^a-z0-9_-]/gi,'').slice(0,12);
      ev('sample_audio_play');
      ev('sample_play',tag);
      meta('SampleAudioPlay',{content_name:tag||'sample'},true);
    }}catch(x){}
  },true);
  // ViewContent once when pricing section is seen
  function watchPricing(){
    try{
      var el=document.getElementById('pricing');
      if(!el||!window.IntersectionObserver)return;
      var seen=false;
      var io=new IntersectionObserver(function(entries){
        for(var i=0;i<entries.length;i++){
          if(entries[i].isIntersecting&&!seen){
            seen=true;
            ev('pricing_view');
            meta('ViewContent',{content_name:'pricing',content_category:'plans',currency:'USD',value:0});
            try{io.disconnect();}catch(e){}
          }
        }
      },{threshold:0.35});
      io.observe(el);
    }catch(e){}
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',watchPricing);
  else watchPricing();
  // Oct 30 2026: resilient Step 1 submit. Sends the lead to FormSubmit in the background
  // and always continues to Stripe checkout, even if FormSubmit is slow or down.
  document.addEventListener('submit',function(e){
    try{var f=e.target; if(!f||!f.classList||!f.classList.contains('cb-step1-form'))return;
      var act=f.getAttribute('action')||''; if(act.indexOf('formsubmit.co/')===-1||!window.fetch||!window.FormData)return;
      if(f.elements['_honey']&&f.elements['_honey'].value)return;
      var next=(f.elements['_next']&&f.elements['_next'].value)||'';
      if(next.indexOf('https://')!==0)return;
      e.preventDefault();
      var em=(f.elements['email']&&f.elements['email'].value)||'';
      if(em&&next.indexOf('buy.stripe.com')!==-1&&next.indexOf('prefilled_email=')===-1)next+=(next.indexOf('?')===-1?'?':'&')+'prefilled_email='+encodeURIComponent(em);
      next=appendStripeAttribution(next);
      try{ if(f.elements['_next']) f.elements['_next'].value=next; }catch(err){}
      var btn=f.querySelector('button[type=submit],input[type=submit],button:not([type])'); if(btn){btn.disabled=true;}
      var done=false; function go(){ if(done)return; done=true; location.href=next; }
      var ctl=window.AbortController?new AbortController():null;
      setTimeout(function(){ if(ctl){try{ctl.abort();}catch(x){}} go(); },4000);
      fetch(act.replace('formsubmit.co/','formsubmit.co/ajax/'),{method:'POST',body:new FormData(f),headers:{'Accept':'application/json'},signal:ctl?ctl.signal:undefined})
        .then(function(r){
          if(!r||!r.ok){hit('step1_fs_fail__'+U); go(); return;}
          return r.json().then(function(j){
            if(!j||j.success===false||j.success==='false'){hit('step1_fs_fail__'+U); go(); return;}
            if(next.indexOf('buy.stripe.com')===-1 && navigator.globalPrivacyControl!==true && typeof window.fbq==='function'){
              try{window.fbq('track','Lead',{value:0,currency:'USD'});}catch(e){}
            }
            go();
          },function(){ go(); });
        },function(){ hit('step1_fs_fail__'+U); go(); });
    }catch(x){}
  },false);
})();
