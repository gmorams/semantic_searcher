interface Props {
  urls: string[];
}

export function Sources({ urls }: Props) {
  if (urls.length === 0) return null;
  return (
    <details className="mt-3 rounded-lg border border-slate-200 bg-white">
      <summary className="cursor-pointer px-3 py-2 text-sm font-medium text-slate-700">
        📚 Fonts ({urls.length})
      </summary>
      <ul className="space-y-1 px-3 pb-3 pt-1 text-sm">
        {urls.map((u) => (
          <li key={u}>
            <a
              href={u}
              target="_blank"
              rel="noreferrer"
              className="break-all text-fibblue hover:underline"
            >
              {u}
            </a>
          </li>
        ))}
      </ul>
    </details>
  );
}
