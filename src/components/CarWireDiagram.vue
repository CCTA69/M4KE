<script setup lang="ts">
import {computed} from 'vue';
import type {ElectricalConnection,ToyPart} from '../viewport/types';
const props=defineProps<{parts:ToyPart[];connections:ElectricalConnection[];selectedId:string|null;labels?:Record<string,{title:string;sub:string}>}>();
const emit=defineEmits<{select:[id:string]}>();
// This is a connectivity diagram, deliberately not a PCB pin-position drawing.
const layout:Record<string,{x:number;y:number;w:number;title:string;sub:string;tag:string}>={
  battery_holder:{x:40,y:50,w:230,title:'4 × AA 电池',sub:'NiMH · 标称 4.8 V',tag:'01 / POWER'},
  power_switch:{x:425,y:50,w:230,title:'总电源开关',sub:'物理断电 · COM / ON',tag:'02 / SWITCH'},
  regulator:{x:810,y:50,w:230,title:'5 V 升降压',sub:'DFR0569 · 只给主控供电',tag:'03 / REGULATOR'},
  microphone:{x:40,y:315,w:230,title:'MAX4466 麦克风',sub:'Adafruit #1063 · 3.3 V',tag:'04 / INPUT'},
  esp32:{x:425,y:315,w:230,title:'ESP32 主控',sub:'DevKitC V4 · WROOM-32E',tag:'05 / CONTROLLER'},
  driver:{x:810,y:315,w:230,title:'双路电机驱动',sub:'DRI0044 · DIR / PWM',tag:'06 / DRIVER'},
  arm_button:{x:40,y:580,w:230,title:'ARM 按钮',sub:'常开自复位 · 按下接地',tag:'07 / ENABLE'},
  motor_L:{x:540,y:580,w:230,title:'左后轮电机',sub:'FIT0094 · 镜像安装',tag:'08 / MOTOR L'},
  motor_R:{x:810,y:580,w:230,title:'右后轮电机',sub:'FIT0094 · 先抬轮确认方向',tag:'09 / MOTOR R'},
};
const height=145;
const nodes=computed(()=>Object.entries(layout).filter(([id])=>props.parts.some(p=>p.id===id)).map(([id,p])=>({id,...p,...props.labels?.[id]})));
const selected=computed(()=>props.connections.find(c=>c.id===props.selectedId));
const endpointLabel=(id:string)=>selected.value?.from.partId===id?selected.value.from.terminal:selected.value?.to.partId===id?selected.value.to.terminal:'';
const involved=(id:string)=>!!selected.value&&[selected.value.from.partId,selected.value.to.partId].includes(id);
function port(id:string,other:string,wireId:string){
  const n=layout[id],o=layout[other];
  const links=props.connections.filter(c=>c.from.partId===id||c.to.partId===id);
  const i=Math.max(0,links.findIndex(c=>c.id===wireId));
  const spread=(i+1)/(links.length+1);
  if(Math.abs(n.x-o.x)<80)return {x:n.x+30+spread*(n.w-60),y:n.y+(o.y>n.y?height:0),dx:0,dy:o.y>n.y?1:-1};
  return {x:n.x+(o.x>n.x?n.w:0),y:n.y+28+spread*86,dx:o.x>n.x?1:-1,dy:0};
}
const routes=computed(()=>props.connections.filter(c=>layout[c.from.partId]&&layout[c.to.partId]).map(c=>{
  const a=port(c.from.partId,c.to.partId,c.id),b=port(c.to.partId,c.from.partId,c.id);
  const bend=Math.min(155,Math.max(60,Math.hypot(a.x-b.x,a.y-b.y)*.35));
  return {...c,a,b,path:`M${a.x},${a.y} C${a.x+a.dx*bend},${a.y+a.dy*bend} ${b.x+b.dx*bend},${b.y+b.dy*bend} ${b.x},${b.y}`};
}).sort((a,b)=>Number(a.id===props.selectedId)-Number(b.id===props.selectedId)));
function chooseNode(id:string){const choices=props.connections.filter(c=>[c.from.partId,c.to.partId].includes(id));if(!choices.length)return;const current=choices.findIndex(c=>c.id===props.selectedId);emit('select',choices[(current+1)%choices.length].id);}
</script>

<template>
  <section class="wire-diagram" aria-label="交互接线图">
    <div class="diagram-intro"><span>CONNECT WITH CONFIDENCE</span><h2>每一条线，都接得明白。</h2><p>点选线路或元件，查看两端接哪里。按右侧顺序，断电后逐条连接。</p></div>
    <div class="diagram-scroll">
      <svg class="diagram-canvas" viewBox="0 0 1080 765" role="group" aria-label="电源、主控、传感器与电机连接关系">
        <defs><pattern id="wire-dots" width="22" height="22" patternUnits="userSpaceOnUse"><circle cx="1" cy="1" r=".75" fill="#536079" opacity=".2"/></pattern></defs>
        <rect width="1080" height="765" fill="url(#wire-dots)"/>
        <g v-for="r in routes" :key="r.id" :data-diagram-wire="r.id" :data-selected="r.id===selectedId" role="button" tabindex="0" :aria-label="`${r.id} ${r.from.terminal} 到 ${r.to.terminal}`" :aria-pressed="r.id===selectedId" @click="emit('select',r.id)" @keydown.enter.prevent="emit('select',r.id)" @keydown.space.prevent="emit('select',r.id)">
          <path :d="r.path" fill="none" :stroke="r.color" :stroke-width="r.id===selectedId?4:1.8" :opacity="r.id===selectedId?1:.14" stroke-linecap="round"/>
          <path class="wire-hit" :d="r.path" fill="none" stroke="transparent" stroke-width="15"/>
          <circle v-for="(p,i) in [r.a,r.b]" :key="i" :cx="p.x" :cy="p.y" :r="r.id===selectedId?5:2.5" :fill="r.color" :opacity="r.id===selectedId?1:.24"/>
        </g>
        <g v-for="n in nodes" :key="n.id" class="diagram-node" :data-node="n.id" :transform="`translate(${n.x},${n.y})`" role="button" tabindex="0" :aria-label="`${n.title}，切换相关线路`" @click="chooseNode(n.id)" @keydown.enter.prevent="chooseNode(n.id)" @keydown.space.prevent="chooseNode(n.id)">
          <rect :width="n.w" :height="height" rx="16" fill="#171e2a" :stroke="involved(n.id)?selected?.color:'#2b3545'" :stroke-width="involved(n.id)?1.8:1"/>
          <text x="20" y="27" font-size="9" letter-spacing="1.1" fill="#7f91ad">{{n.tag}}</text>
          <text x="20" y="58" font-size="18" font-weight="600" fill="#ebf0f8">{{n.title}}</text>
          <text x="20" y="82" font-size="11" fill="#93a4bb">{{n.sub}}</text>
          <path :d="`M20,99 H${n.w-20}`" stroke="#ffffff0e"/>
          <circle cx="24" cy="121" r="3" :fill="involved(n.id)?selected?.color:'#536179'"/>
          <text x="36" y="125" font-size="11" :fill="involved(n.id)?'#f0f5fd':'#75849b'">{{endpointLabel(n.id)||'点按查看相关接线'}}</text>
        </g>
      </svg>
    </div>
    <div class="diagram-disclaimer"><span>● 选中线路高亮</span><span>连通关系示意，不是 PCB 针脚位置图；接线以模块丝印为准。</span></div>
  </section>
</template>

<style scoped>
.wire-diagram{display:flex;flex:1;min-height:0;flex-direction:column;background:radial-gradient(ellipse at 55% 38%,#192335 0%,#0f141e 66%);overflow:auto}.diagram-intro{padding:25px 32px 0}.diagram-intro>span{font-size:9px;letter-spacing:.18em;color:#87baa9}.diagram-intro h2{font-size:25px;font-weight:550;letter-spacing:-.025em;margin:9px 0}.diagram-intro p{font-size:12px;color:#8e9fb7;margin:0;line-height:1.8}.diagram-scroll{flex:1;min-height:360px;display:flex;align-items:center;justify-content:center;overflow:auto;padding:8px 20px}.diagram-canvas{display:block;width:100%;height:100%;min-height:360px;max-height:780px;font-family:inherit}.diagram-node,.wire-hit{cursor:pointer}.diagram-node:focus-visible rect,[data-diagram-wire]:focus-visible .wire-hit{stroke:#fff;stroke-width:2;outline:none}.diagram-node:focus-visible,[data-diagram-wire]:focus-visible{outline:none}.diagram-disclaimer{display:flex;gap:22px;justify-content:space-between;padding:10px 28px 17px;color:#8596ad;font-size:10px;line-height:1.7}.diagram-disclaimer span:first-child{color:#a2c6b8;white-space:nowrap}@media(max-width:700px){.diagram-intro{padding:20px}.diagram-intro h2{font-size:21px}.diagram-scroll{display:block;padding:5px 0;min-height:470px}.diagram-canvas{width:790px;height:560px;max-width:none}.diagram-disclaimer{padding:12px 20px;flex-direction:column;gap:5px}}
</style>
