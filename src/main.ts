import { createApp, defineAsyncComponent } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import "./studio-vue.css";
const Root = ['echo-f1-v1','echo-f1-cn-v2'].includes(new URLSearchParams(location.search).get('build') || '')
  ? defineAsyncComponent(() => import('./components/AuthoredBuild.vue')) : App;
createApp(Root).use(createPinia()).mount("#root");
