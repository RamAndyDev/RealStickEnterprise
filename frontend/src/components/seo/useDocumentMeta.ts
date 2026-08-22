import { useEffect } from 'react';

const DEFAULT_DESCRIPTION =
  'RealStick — Natural Popsicles & Kulfi. Real Fruits. Real Goodness. Zero artificial colours, flavours, or preservatives.';

/** Matches the public `<title>` in `frontend/index.html`. */
export const DEFAULT_DOCUMENT_TITLE = 'RealStick™ — Natural Popsicles & Kulfi';

type DocumentMetaEntry = {
  title: string;
  description: string;
};

const metaStack: DocumentMetaEntry[] = [];

function applyTopMeta() {
  const top = metaStack[metaStack.length - 1];
  document.title = top?.title ?? DEFAULT_DOCUMENT_TITLE;

  let meta = document.querySelector('meta[name="description"]');
  if (!meta) {
    meta = document.createElement('meta');
    meta.setAttribute('name', 'description');
    document.head.appendChild(meta);
  }
  meta.setAttribute('content', top?.description ?? DEFAULT_DESCRIPTION);
}

export function useDocumentMeta(title: string | null | undefined, description: string = DEFAULT_DESCRIPTION) {
  useEffect(() => {
    if (!title) return undefined;

    const entry: DocumentMetaEntry = { title, description };
    metaStack.push(entry);
    applyTopMeta();

    return () => {
      const index = metaStack.lastIndexOf(entry);
      if (index >= 0) {
        metaStack.splice(index, 1);
      }
      applyTopMeta();
    };
  }, [title, description]);
}
