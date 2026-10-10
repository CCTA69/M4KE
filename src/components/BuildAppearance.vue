<script setup lang="ts">
import {Download,Palette} from '@lucide/vue';
export type BuildAppearancePlan = {
  id:string; title:string; summary:string; previewNote:string;
  palette:{name:string;color:string}[]; rules:string[];
  artifacts:{label:string;file:string;slot:string;colour:string;note:string;status:string}[];
};
defineProps<{plan:BuildAppearancePlan;base:string;compact?:boolean}>();
</script>

<template>
  <section class="build-appearance" :class="{compact}" aria-label="车身配色方案">
    <div class="finish-label"><Palette :size="14"/> ECHO / EMBER EDITION</div>
    <h2>{{plan.title}}</h2><p>{{plan.summary}}</p>
    <div class="finish-swatches"><span v-for="s in plan.palette" :key="s.name"><i :style="{background:s.color}"/>{{s.name}}</span></div>
    <small>{{plan.previewNote}}</small>
    <template v-if="!compact">
      <div class="finish-downloads"><a v-for="a in plan.artifacts" :key="a.file" :href="base+'/files/'+a.file" download><Download :size="18"/><div><strong>{{a.label}}</strong><span>AMS {{a.slot}} · {{a.colour}}</span><small>{{a.note}}</small></div></a></div>
      <p class="finish-caution">这是两份<b>可编辑、未切片</b>工程，不是已发送任务。槽位编号是历史示例，不代表当前 AMS 耗材；必须核对料卷材质并重新映射，支撑专用料不能打印车身。保留 0.4 mm / 纹理 PEI / 100% 比例。每盘清床，再同步 AMS、切片、核对颜色后打印。</p>
      <details><summary>材料与配色说明</summary><ul><li v-for="r in plan.rules" :key="r">{{r}}</li></ul></details>
    </template>
  </section>
</template>

<style scoped>
.build-appearance{margin:20px 0;padding:25px;border:1px solid #d1ac9b33;border-radius:18px;background:radial-gradient(ellipse at 100% 0,#65323944,transparent 62%),#171d26;color:#f2eee9}.finish-label{display:flex;gap:8px;align-items:center;font-size:9px;letter-spacing:.17em;color:#c18b8e}.build-appearance h2{font-size:27px;letter-spacing:-.05em;margin:11px 0}.build-appearance p{font-size:12px;line-height:1.8;color:#b6bac5}.finish-swatches{display:flex;gap:14px;flex-wrap:wrap;margin:18px 0}.finish-swatches span{display:flex;gap:7px;align-items:center;font-size:10px;color:#c7cbd2}.finish-swatches i{display:inline-block;width:19px;height:19px;border-radius:50%;box-shadow:inset 0 0 0 1px #ffffff33}.finish-swatches span:first-child i{background:linear-gradient(100deg,#211d23 0%,#5b232b 40%,#a85451 100%)!important}.build-appearance small{display:block;color:#8d98aa;font-size:10px;line-height:1.75}.finish-downloads{display:grid;grid-template-columns:1fr 1fr;gap:12px;margin:20px 0}.finish-downloads a{display:flex;gap:12px;padding:18px;border-radius:12px;border:1px solid #d7dce533;background:#e7e4df0b;text-decoration:none;color:#f1eee9}.finish-downloads a:hover{background:#ffffff13}.finish-downloads a:focus-visible{outline:2px solid #dfb1b2;outline-offset:4px}.finish-downloads a>svg{flex-shrink:0;margin-top:2px}.finish-downloads strong{display:block;font-size:14px}.finish-downloads span{display:block;font-size:11px;color:#d8adaf;margin:7px 0}.finish-caution{border-left:2px solid #b9946c;padding-left:12px}.build-appearance details{font-size:11px;color:#9caabd;line-height:1.9}.build-appearance summary{cursor:pointer}.compact{margin:0;padding:19px;border:0;border-bottom:1px solid #ffffff12;border-radius:0}.compact h2{font-size:22px}.compact p{font-size:11px}.compact .finish-swatches{flex-direction:column;gap:8px;margin:13px 0}@media(max-width:650px){.finish-downloads{grid-template-columns:1fr}}
</style>
