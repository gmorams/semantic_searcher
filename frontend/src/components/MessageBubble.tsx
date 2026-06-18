import clsx from "clsx";
import type { Message } from "../types";
import { Sources } from "./Sources";
import { TechDetails } from "./TechDetails";

interface Props {
  message: Message;
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === "user";
  return (
    <div className={clsx("flex gap-3", isUser ? "justify-end" : "justify-start")}>
      {!isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-fibblue/10 text-base">
          🔍
        </div>
      )}
      <div
        className={clsx(
          "max-w-[78%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
          isUser ? "bg-fibblue text-white" : "bg-white text-slate-800 shadow-sm ring-1 ring-slate-200",
        )}
      >
        <div className="whitespace-pre-wrap">{message.content}</div>
        {!isUser && message.details && (
          <>
            <Sources urls={message.details.sources} />
            <TechDetails details={message.details} />
          </>
        )}
      </div>
      {isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-slate-200 text-base">
          🧑‍🎓
        </div>
      )}
    </div>
  );
}
