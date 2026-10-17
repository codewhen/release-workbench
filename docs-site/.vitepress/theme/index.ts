import DefaultTheme from 'vitepress/theme';
import { onMounted, onUnmounted, watch, nextTick } from 'vue';
import { useRoute } from 'vitepress';
import './style.css';
export default {
  extends: DefaultTheme,
  setup() {
    const route = useRoute();
    const enlarge = (event: Event) => {
      const target = event.target;
      if (!(target instanceof HTMLImageElement) || !target.closest('.vp-doc')) return;
      const dialog = document.createElement('dialog');
      dialog.className = 'screenshot-dialog';
      dialog.setAttribute('aria-label', target.alt || 'Enlarged screenshot');
      const close = document.createElement('button');
      close.textContent = 'Close screenshot';
      close.addEventListener('click', () => dialog.close());
      const enlarged = target.cloneNode() as HTMLImageElement;
      enlarged.removeAttribute('tabindex'); enlarged.removeAttribute('role'); enlarged.removeAttribute('aria-label');
      dialog.append(close, enlarged);
      dialog.addEventListener('click', e => { if (e.target === dialog) dialog.close(); });
      dialog.addEventListener('close', () => { dialog.remove(); target.focus(); });
      document.body.append(dialog); dialog.showModal(); close.focus();
    };
    const prepare = () => document.querySelectorAll<HTMLImageElement>('.vp-doc img').forEach(img => {
      img.tabIndex = 0; img.setAttribute('role', 'button'); img.setAttribute('aria-label', 'Enlarge: ' + img.alt);
    });
    const key = (event: KeyboardEvent) => {
      if ((event.key === 'Enter' || event.key === ' ') && event.target instanceof HTMLImageElement) {
        event.preventDefault(); enlarge(event);
      }
    };
    onMounted(() => { prepare(); document.addEventListener('click', enlarge); document.addEventListener('keydown', key); });
    watch(() => route.path, async () => { await nextTick(); prepare(); });
    onUnmounted(() => { document.removeEventListener('click', enlarge); document.removeEventListener('keydown', key); });
  },
};
