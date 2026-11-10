const toggle=document.querySelector('.mobile-nav-toggle');
toggle?.addEventListener('click',()=>{const nav=document.querySelector('.topbar nav');nav?.classList.toggle('nav-open');toggle.setAttribute('aria-expanded',nav?.classList.contains('nav-open')?'true':'false');});
document.querySelectorAll('.topbar nav a').forEach(link=>link.addEventListener('click',()=>document.querySelector('.topbar nav')?.classList.remove('nav-open')));
