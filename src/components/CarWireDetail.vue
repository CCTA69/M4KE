<script setup lang="ts">
import {ArrowRight,ChevronLeft,ChevronRight,AlertTriangle} from '@lucide/vue';
import type {ElectricalConnection,ToyPart} from '../viewport/types';
defineProps<{connection:ElectricalConnection;parts:ToyPart[];index:number;total:number}>();
defineEmits<{previous:[];next:[]}>();
const names:Record<string,string>={power:'电源线',ground:'地线 / 回流',signal:'控制 / 信号',motor:'电机输出'};
const label=(parts:ToyPart[],id:string)=>parts.find(p=>p.id===id)?.name.trim()||id;
</script>
<template>
  <section class="wire-detail" :style="{'--wire-color':connection.color}" aria-label="选中线路说明">
    <div class="wire-detail-top"><span>{{connection.id}} <i/> {{names[connection.kind]||connection.kind}}</span><div><button aria-label="上一条线路" :disabled="index<=0" @click="$emit('previous')"><ChevronLeft :size="15"/></button><small>{{index+1}} / {{total}}</small><button aria-label="下一条线路" :disabled="index>=total-1" @click="$emit('next')"><ChevronRight :size="15"/></button></div></div>
    <div class="wire-endpoint"><span>从这里接出</span><p>{{label(parts,connection.from.partId)}}</p><strong>{{connection.from.terminal}}</strong></div>
    <div class="wire-connection-line"><i/><ArrowRight :size="15"/><small>{{connection.wireAwg}} AWG · 多股软线</small></div>
    <div class="wire-endpoint"><span>接到这里</span><p>{{label(parts,connection.to.partId)}}</p><strong>{{connection.to.terminal}}</strong></div>
    <p v-if="connection.note" class="wire-caution"><AlertTriangle :size="14"/><span>{{connection.note}}</span></p>
  </section>
</template>
<style scoped>
.wire-detail{padding:19px 19px 20px;border-bottom:1px solid #ffffff12;background:linear-gradient(135deg,#19222f,#141b26)}.wire-detail-top{display:flex;align-items:center;justify-content:space-between;gap:9px;margin-bottom:20px}.wire-detail-top>span{font:600 11px/1.5 inherit;display:flex;align-items:center;gap:8px;color:var(--wire-color)}.wire-detail-top i{width:3px;height:3px;background:currentColor;border-radius:50%}.wire-detail-top>div{display:flex;align-items:center;gap:3px}.wire-detail-top button{background:transparent;border:0;color:#b7c4d8;padding:4px}.wire-detail-top button:disabled{opacity:.3}.wire-detail-top small{font-size:10px;color:#8c9cb3;white-space:nowrap}.wire-endpoint>span{font-size:9px;color:#788ba4;letter-spacing:.04em}.wire-endpoint p{font-size:11px;color:#aebdd3;line-height:1.5;margin:4px 0}.wire-endpoint strong{font-size:19px;font-weight:600;display:block;color:#edf4ff;overflow-wrap:anywhere}.wire-connection-line{display:flex;align-items:center;color:var(--wire-color);gap:7px;margin:15px 0}.wire-connection-line i{width:35px;height:2px;background:var(--wire-color)}.wire-connection-line small{font-size:10px;color:#a1b0c5;margin-left:5px}.wire-caution{display:flex;gap:8px;padding:12px;background:#dba7540b;border:1px solid #dba75426;border-radius:8px;margin:18px 0 0;color:#e1bd8d;font-size:11px;line-height:1.8}.wire-caution svg{flex:none;margin-top:3px}
</style>
