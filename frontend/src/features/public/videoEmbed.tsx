export type VideoEmbed =
  | { kind: 'youtube'; src: string }
  | { kind: 'vimeo'; src: string }
  | { kind: 'file'; src: string }
  | { kind: 'link'; href: string };

function youtubeId(url: URL): string | null {
  if (url.hostname === 'youtu.be') {
    return url.pathname.replace('/', '') || null;
  }
  if (url.hostname.endsWith('youtube.com') || url.hostname.endsWith('youtube-nocookie.com')) {
    if (url.pathname.startsWith('/embed/')) return url.pathname.split('/')[2] || null;
    return url.searchParams.get('v');
  }
  return null;
}

function vimeoId(url: URL): string | null {
  if (!url.hostname.endsWith('vimeo.com')) return null;
  const parts = url.pathname.split('/').filter(Boolean);
  const last = parts[parts.length - 1];
  return last && /^\d+$/.test(last) ? last : null;
}

export function parseVideoEmbed(raw: string | null | undefined): VideoEmbed | null {
  if (!raw) return null;
  let url: URL;
  try {
    url = new URL(raw);
  } catch {
    return null;
  }
  if (url.protocol !== 'https:') return null;

  const yt = youtubeId(url);
  if (yt) {
    return { kind: 'youtube', src: `https://www.youtube-nocookie.com/embed/${encodeURIComponent(yt)}` };
  }
  const vimeo = vimeoId(url);
  if (vimeo) {
    return { kind: 'vimeo', src: `https://player.vimeo.com/video/${encodeURIComponent(vimeo)}` };
  }
  if (/\.(mp4|webm|ogg)$/i.test(url.pathname)) {
    return { kind: 'file', src: url.toString() };
  }
  return { kind: 'link', href: url.toString() };
}

export function VideoEmbedFrame({ url, title }: { url: string; title: string }) {
  const embed = parseVideoEmbed(url);
  if (!embed) return null;
  if (embed.kind === 'youtube' || embed.kind === 'vimeo') {
    return (
      <iframe
        src={embed.src}
        title={title}
        className="h-full w-full"
        allow="accelerometer; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
        allowFullScreen
      />
    );
  }
  if (embed.kind === 'file') {
    return (
      <video className="h-full w-full" controls preload="metadata" src={embed.src}>
        <track kind="captions" />
      </video>
    );
  }
  return (
    <a
      href={embed.href}
      target="_blank"
      rel="noreferrer noopener"
      className="flex h-full items-center justify-center bg-[#0D4F2E] px-4 text-center text-sm font-semibold text-white"
    >
      Watch video
    </a>
  );
}
