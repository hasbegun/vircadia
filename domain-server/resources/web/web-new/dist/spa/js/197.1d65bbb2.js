"use strict";(self["webpackChunkvircadia_domain_dashboard"]=self["webpackChunkvircadia_domain_dashboard"]||[]).push([[197],{7197:(t,a,n)=>{n.r(a),n.d(a,{default:()=>m});var e=n(3673);const i={id:"firstTimeWizardContainer"};function s(t,a,n,s,o,r){const u=(0,e.up)("router-view"),h=(0,e.up)("q-page-container"),d=(0,e.up)("q-layout");return(0,e.wg)(),(0,e.j4)(d,{id:"vantaBG",view:"hHh lpR fFf"},{default:(0,e.w5)((()=>[(0,e.Wm)(h,null,{default:(0,e.w5)((()=>[(0,e._)("div",i,[(0,e.Wm)(u)])])),_:1})])),_:1})}n(71);var o=n(3991);const r=(0,e.aZ)({name:"FirstTimeWizard",data(){return{vantaBG:null,vantaRings:null,refreshVantaTimeout:null,DELAY_REFRESH_VANTA:500}},async mounted(){window.THREE=o,this.vantaRings=(await n.e(736).then(n.t.bind(n,5160,23))).default,this.initVanta(),visualViewport.addEventListener("resize",this.onResize)},methods:{onResize(){this.refreshVantaTimeout&&clearTimeout(this.refreshVantaTimeout),this.refreshVantaTimeout=setTimeout((()=>{this.initVanta(),this.refreshVantaTimeout=null}),this.DELAY_REFRESH_VANTA)},initVanta(){this.vantaBG&&this.vantaBG.destroy(),this.vantaBG=this.vantaRings({el:"#vantaBG",mouseControls:!1,touchControls:!1,gyroControls:!1,minHeight:200,minWidth:200,scale:1,scaleMobile:1,color:0})}},beforeUnmount(){this.vantaBG&&this.vantaBG.destroy()}});var u=n(4899),h=n(2652),d=n(7518),l=n.n(d);r.render=s;const m=r;l()(r,"components",{QLayout:u.Z,QPageContainer:h.Z})}}]);