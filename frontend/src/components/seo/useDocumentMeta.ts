import { useEffect } from 'react';

const DEFAULT_DESCRIPTION =
  'RealStick — Natural Popsicles & Kulfi. Real Fruits. Real Goodness. Zero artificial colours, flavours, or preservatives.';

export function useDocumentMeta(title: string, description: string = DEFAULT_DESCRIPTION) {
  useEffect(() => {
    document.title = title;
    let meta = document.querySelector('meta[name="description"]');
    if (!meta) {
      meta = document.createElement('meta');
      meta.setAttribute('name', 'description');
      document.head.appendChild(meta);
    }
    meta.setAttribute('content', description);
  }, [title, description]);
}
