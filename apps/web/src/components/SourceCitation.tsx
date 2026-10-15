import type { SourceItem } from "@/lib/api";

interface Props {
  source: SourceItem;
}

export function SourceCitation({ source }: Props) {
  const label = source.page
    ? `${source.document_name} hal. ${source.page}`
    : source.document_name;

  return (
    <span
      className="inline-flex items-center gap-1 rounded-full bg-blue-50 px-2.5 py-0.5 text-xs font-medium text-blue-700 border border-blue-100"
      title={`Chunk ID: ${source.chunk_id}`}
      role="note"
      aria-label={`Sumber: ${label}`}
    >
      <svg
        aria-hidden="true"
        className="h-3 w-3"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        strokeWidth={2}
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
        />
      </svg>
      {label}
    </span>
  );
}
