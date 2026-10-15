import type { MessageOut } from "@/lib/api";
import { SourceCitation } from "./SourceCitation";

interface Props {
  message: MessageOut;
}

export function ChatMessage({ message }: Props) {
  const isUser = message.role === "user";

  return (
    <div
      className={`flex gap-3 ${isUser ? "justify-end" : "justify-start"}`}
      role="article"
      aria-label={isUser ? "Pesan Anda" : "Jawaban AI"}
    >
      {!isUser && (
        <div
          aria-hidden="true"
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-blue-600 text-white text-xs font-bold"
        >
          AI
        </div>
      )}

      <div className={`max-w-[75%] ${isUser ? "items-end" : "items-start"} flex flex-col gap-1`}>
        <div
          className={`rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
            isUser
              ? "bg-blue-600 text-white rounded-tr-sm"
              : "bg-white border border-gray-200 text-gray-800 rounded-tl-sm shadow-sm"
          }`}
        >
          <p className="whitespace-pre-wrap">{message.content}</p>
        </div>

        {!isUser && message.sources && message.sources.length > 0 && (
          <div className="mt-1 flex flex-col gap-1">
            <span className="text-xs text-gray-500">Sumber:</span>
            <div className="flex flex-wrap gap-1.5">
              {message.sources.map((src) => (
                <SourceCitation key={src.chunk_id} source={src} />
              ))}
            </div>
          </div>
        )}
      </div>

      {isUser && (
        <div
          aria-hidden="true"
          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gray-200 text-gray-600 text-xs font-bold"
        >
          Anda
        </div>
      )}
    </div>
  );
}
