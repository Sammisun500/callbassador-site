(function(){
  var form = document.querySelector('form.cb-wizard');
  if(!form) return;
  var steps = Array.prototype.slice.call(form.querySelectorAll('.wiz-step'));
  var dots = Array.prototype.slice.call(document.querySelectorAll('[data-wiz-dot]'));
  var planInp = document.getElementById('cb-plan-input');
  var nextInp = form.querySelector('input[name="_next"]');
  var pathInp = form.querySelector('input[name="signup_path"]');
  var summary = document.getElementById('wiz-summary');
  var current = 1;
  var offer = false;
  var demoChosen = false;
  var PRO_STD = 'Pro — $149/mo (14-day free trial)';
  var PRO_OFFER = 'Pro — $99/mo (November Special · 400 min, 24/7)';
  var DEMO = 'Just hear a free custom demo first';
  var URLS = {
    'Pro — $99/mo (November Special · 400 min, 24/7)':'https://buy.stripe.com/00waEXbTG6AacLs05j1Jm01',
    'Starter — $79/mo (14-day free trial)':'https://buy.stripe.com/6oU00j4re9Mm6n4g4h1Jm03',
    'Pro — $149/mo (14-day free trial)':'https://buy.stripe.com/8x27sL6zme2C3aS19n1Jm02',
    'Crew — $249/mo (14-day free trial)':'https://buy.stripe.com/14AeVd7DqcYycLs05j1Jm00',
    'Growth — $249/mo (14-day free trial)':'https://buy.stripe.com/14AeVd7DqcYycLs05j1Jm00',
    'Just hear a free custom demo first':'https://callbassador.com/thanks.html'
  };
  function planValue(){
    if(demoChosen) return DEMO;
    if(offer) return PRO_OFFER;
    var r = form.querySelector('input[name="cb_plan_choice"]:checked');
    return (r && r.value) || PRO_STD;
  }
  function destination(plan, email){
    var base = URLS[plan];
    if(!base){
      if(plan && plan.indexOf('demo first')!==-1) base = URLS[DEMO];
      else if(plan && plan.indexOf('$79')!==-1) base = URLS['Starter — $79/mo (14-day free trial)'];
      else if(plan && plan.indexOf('$249')!==-1) base = URLS['Crew — $249/mo (14-day free trial)'];
      else base = URLS[PRO_STD];
    }
    var em = (email||'').trim();
    if(em && base.indexOf('https://buy.stripe.com/')===0){
      return base + (base.indexOf('?')===-1?'?':'&') + 'prefilled_email=' + encodeURIComponent(em);
    }
    return base;
  }
  function sync(){
    var plan = planValue();
    if(planInp) planInp.value = plan;
    var email = (form.elements.email && form.elements.email.value) || '';
    if(nextInp) nextInp.value = destination(plan, email);
    if(pathInp) pathInp.value = (plan===DEMO) ? 'free_demo' : 'trial';
  }
  function visibleLabel(plan){
    if(plan===PRO_OFFER) return 'Pro — price shown in the pricing section, then confirmed on Stripe';
    if(plan===DEMO) return 'Free custom demo (no card)';
    return plan;
  }
  function fillSummary(){
    if(!summary) return;
    var plan = planValue();
    var rows = [
      ['Name', (form.elements.name||{}).value||''],
      ['Business', (form.elements.business_name||{}).value||''],
      ['Trade', (form.elements.trade||{}).value||''],
      ['Mobile', (form.elements.phone||{}).value||''],
      ['Email', (form.elements.email||{}).value||''],
      ['Plan', visibleLabel(plan)],
      ['Call alerts', (form.elements.call_alerts||{}).value||'']
    ];
    summary.innerHTML = rows.map(function(r){
      return '<div><dt>'+r[0]+'</dt><dd>'+String(r[1]).replace(/[&<>]/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;'}[c];})+'</dd></div>';
    }).join('');
  }
  function show(n){
    current = n;
    steps.forEach(function(s){
      var on = s.getAttribute('data-step')===String(n);
      if(on) s.removeAttribute('hidden'); else s.setAttribute('hidden','');
      s.querySelectorAll('[data-req]').forEach(function(el){ el.required = on; });
    });
    dots.forEach(function(d){
      d.classList.toggle('is-on', d.getAttribute('data-wiz-dot')===String(n));
    });
    if(n===3){ sync(); fillSummary(); }
    var top = document.getElementById('signup');
    if(top && n>1) top.scrollIntoView({behavior:'smooth',block:'start'});
  }
  function stepValid(n){
    var step = form.querySelector('.wiz-step[data-step="'+n+'"]');
    if(!step) return true;
    var ok = true;
    step.querySelectorAll('[data-req]').forEach(function(el){
      el.required = true;
      if(!el.checkValidity()) ok = false;
    });
    if(!ok) form.reportValidity();
    return ok;
  }
  form.querySelectorAll('[data-wiz-next]').forEach(function(btn){
    btn.addEventListener('click', function(){
      if(!stepValid(current)) return;
      sync();
      show(current+1);
    });
  });
  form.querySelectorAll('[data-wiz-back]').forEach(function(btn){
    btn.addEventListener('click', function(){ show(current-1); });
  });
  form.querySelectorAll('input[name="cb_plan_choice"]').forEach(function(r){
    r.addEventListener('change', function(){ offer = false; demoChosen = false; sync(); });
  });
  form.querySelectorAll('.cb-demo-path').forEach(function(btn){
    btn.addEventListener('click', function(){
      if(current===1 && !stepValid(1)) return;
      if(current<3 && !form.elements.call_alerts.value){
        show(2);
        form.elements.call_alerts.focus();
        return;
      }
      demoChosen = true;
      offer = false;
      sync();
      form.requestSubmit();
    });
  });
  document.querySelectorAll('a[data-plan]').forEach(function(a){
    a.addEventListener('click', function(){
      var v = a.getAttribute('data-plan')||'';
      if(v.indexOf('November')!==-1 || v.indexOf('$99')!==-1){
        offer = true;
        var pro = form.querySelector('input[name="cb_plan_choice"][value="'+PRO_STD+'"]');
        if(pro) pro.checked = true;
      } else if(v.indexOf('demo first')!==-1){
        offer = false;
      } else {
        offer = false;
        var match = form.querySelector('input[name="cb_plan_choice"][value="'+v+'"]');
        if(!match && v.indexOf('$249')!==-1) match = form.querySelector('input[name="cb_plan_choice"][value="Crew — $249/mo (14-day free trial)"]');
        if(!match && v.indexOf('Starter')!==-1) match = form.querySelector('input[name="cb_plan_choice"][value="Starter — $79/mo (14-day free trial)"]');
        if(match) match.checked = true;
      }
      sync();
    });
  });
  try{
    var q = new URLSearchParams(location.search).get('plan')||'';
    if(q==='pro99'){
      offer = true;
      var pro = form.querySelector('input[name="cb_plan_choice"][value="'+PRO_STD+'"]');
      if(pro) pro.checked = true;
    }
  }catch(e){}
  form.addEventListener('submit', function(){
    sync();
    if(typeof window.fbq==='function'){
      try{window.fbq('trackCustom','SubmitStep1Trial');}catch(e){}
    }
    try{
      var bName = (form.elements.business_name&&form.elements.business_name.value)||'';
      var lead = {
        name:(form.elements.name&&form.elements.name.value)||'',
        business_name:bName,
        business:bName,
        phone:(form.elements.phone&&form.elements.phone.value)||'',
        email:(form.elements.email&&form.elements.email.value)||'',
        trade:(form.elements.trade&&form.elements.trade.value)||'',
        plan:(form.elements.plan&&form.elements.plan.value)||'',
        call_alerts:(form.elements.call_alerts&&form.elements.call_alerts.value)||'',
        signup_path:(form.elements.signup_path&&form.elements.signup_path.value)||''
      };
      var raw = JSON.stringify(lead);
      try{sessionStorage.setItem('cb_trial_lead',raw);}catch(e){}
      try{localStorage.setItem('cb_trial_lead',raw);}catch(e){}
    }catch(err){}
  });
  show(1);
  sync();
})();
