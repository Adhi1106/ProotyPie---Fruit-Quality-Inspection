"use client";

/* eslint-disable @next/next/no-img-element */

import { ChangeEvent, DragEvent, FormEvent, useEffect, useMemo, useRef, useState } from "react";
import { fetchStorageRecommendation, getSpotlightFact, inspectImage, sendChat } from "../lib/api";
import type { ChatMessage, ChatSession, InspectionResult, Recommendation } from "../types";

const spotlightFruits = [
  {
    name: "Pomegranate",
    image:
      "https://lh3.googleusercontent.com/aida-public/AB6AXuCmiajLo0yTk9T7JKoOTsWexyf3c9q853EYJodZgmoV_MSx4HWiMMXMwCIXHEfVDGEAe_2hdkoal_dmwzb8q_PQul0B0EX8McYMKqBJojeNbR8XHZPTGPW2359qFECmAGjiVf5YyRfaTK7UCOcTUjmQdUpKX1qTtoGwMHdwEu7CCqaGmT-DJNWOVh_e_fLKoOc71yk1hH9-IIL5tJ_Ium5oZ2DyVLYhczSaw2kJaqORAF5LWQ55RpgqYPwb7vNrcCP7eke99vNTYrkt",
    fallback:
      "Rich in antioxidants, pomegranates can last up to 2 months when stored properly in a cool, dry place."
  },
  {
    name: "Banana",
    image:
      "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8a/Banana-Whole-and-Split.jpg/640px-Banana-Whole-and-Split.jpg",
    fallback: "Bananas are botanically classified as berries, but strawberries and raspberries are not."
  },
  {
    name: "Apple",
    image: "https://upload.wikimedia.org/wikipedia/commons/thumb/1/15/Red_Apple.jpg/640px-Red_Apple.jpg",
    fallback: "Apple fruits ripen up to ten times faster at room temperature than when refrigerated."
  },
  {
    name: "Orange",
    image:
      "https://upload.wikimedia.org/wikipedia/commons/thumb/4/43/Oranges_and_orange_juice.jpg/640px-Oranges_and_orange_juice.jpg",
    fallback: "The white pith beneath an orange peel contains nearly as much vitamin C as the flesh itself."
  }
];

const defaultSessions: ChatSession[] = [
  {
    id: "default-chat",
    title: "New chat",
    messages: []
  }
];

function makeId() {
  return typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function timeLabel() {
  return new Intl.DateTimeFormat("en", {
    hour: "numeric",
    minute: "2-digit"
  }).format(new Date());
}

function ChatSvgIcon({ name, className = "h-5 w-5" }: { name: "message" | "menu" | "bot" | "close" | "plus" | "edit" | "trash" | "send"; className?: string }) {
  const common = {
    className,
    fill: "none",
    stroke: "currentColor",
    strokeLinecap: "round" as const,
    strokeLinejoin: "round" as const,
    strokeWidth: 2,
    viewBox: "0 0 24 24",
    "aria-hidden": true
  };

  if (name === "message") {
    return (
      <svg {...common}>
        <path d="M21 12a8 8 0 0 1-8 8H7l-4 3v-6a8 8 0 1 1 18-5Z" />
        <path d="M8 11h8" />
        <path d="M8 15h5" />
      </svg>
    );
  }
  if (name === "menu") {
    return (
      <svg {...common}>
        <path d="M4 7h16" />
        <path d="M4 12h16" />
        <path d="M4 17h16" />
      </svg>
    );
  }
  if (name === "bot") {
    return (
      <svg {...common}>
        <path d="M12 4v3" />
        <rect x="6" y="7" width="12" height="10" rx="3" />
        <path d="M9 12h.01" />
        <path d="M15 12h.01" />
        <path d="M9.5 15h5" />
      </svg>
    );
  }
  if (name === "close") {
    return (
      <svg {...common}>
        <path d="M6 6l12 12" />
        <path d="M18 6L6 18" />
      </svg>
    );
  }
  if (name === "plus") {
    return (
      <svg {...common}>
        <path d="M12 5v14" />
        <path d="M5 12h14" />
      </svg>
    );
  }
  if (name === "edit") {
    return (
      <svg {...common}>
        <path d="M12 20h9" />
        <path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z" />
      </svg>
    );
  }
  if (name === "trash") {
    return (
      <svg {...common}>
        <path d="M4 7h16" />
        <path d="M10 11v6" />
        <path d="M14 11v6" />
        <path d="M6 7l1 14h10l1-14" />
        <path d="M9 7V4h6v3" />
      </svg>
    );
  }
  return (
    <svg {...common}>
      <path d="M22 2 11 13" />
      <path d="m22 2-7 20-4-9-9-4Z" />
    </svg>
  );
}

function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <main className="min-h-screen overflow-x-hidden bg-background text-on-surface">
      <div className="fixed inset-0 -z-10 bg-[radial-gradient(circle_at_15%_50%,rgba(253,172,211,0.08),transparent_28%),radial-gradient(circle_at_88%_24%,rgba(80,45,85,0.05),transparent_28%)]" />
      {children}
    </main>
  );
}

function Sidebar({
  spotlightIndex,
  spotlightFact,
  onNext
}: {
  spotlightIndex: number;
  spotlightFact: string;
  onNext: () => void;
}) {
  const fruit = spotlightFruits[spotlightIndex];

  return (
    <aside className="fixed left-0 top-0 z-30 hidden h-screen w-72 flex-col border-r border-white/50 bg-white/30 shadow-2xl shadow-primary-container/10 backdrop-blur-3xl md:flex">
      <div className="flex h-full flex-col p-8">
        <div>
          <h1 className="text-[28px] font-bold leading-none tracking-[-0.02em] text-primary">ProotyPie</h1>
          <p className="mt-3 text-[16px] text-secondary">AI Freshness Guard</p>
        </div>

        <section className="glass-card spotlight-card mt-auto p-4">
          <p className="text-[14px] font-semibold uppercase tracking-[0.05em] text-secondary">Fruit Spotlight</p>
          <h2 className="mt-6 text-[22px] font-semibold leading-7 text-primary">{fruit.name}</h2>
          <p className="mt-3 text-[15px] leading-6 text-on-surface-variant">{spotlightFact || fruit.fallback}</p>
          <button
            className="mt-5 inline-flex text-[15px] font-semibold text-secondary transition hover:translate-x-0.5 hover:text-primary"
            onClick={onNext}
          >
            Next &gt;
          </button>
        </section>
      </div>
    </aside>
  );
}

function Header() {
  return (
    <header className="flex w-full items-center px-margin-mobile py-6 md:px-margin-desktop">
      <h1 className="text-[24px] font-bold leading-8 tracking-[-0.01em] text-primary md:text-[32px] md:leading-10">
        Check Before Consuming
      </h1>
    </header>
  );
}

function UploadDropzone({
  file,
  previewUrl,
  isAnalyzing,
  onFile,
  onInspect
}: {
  file: File | null;
  previewUrl: string | null;
  isAnalyzing: boolean;
  onFile: (file: File) => void;
  onInspect: () => void;
}) {
  const inputRef = useRef<HTMLInputElement | null>(null);

  function chooseFile(event: ChangeEvent<HTMLInputElement>) {
    const nextFile = event.target.files?.[0];
    if (nextFile) onFile(nextFile);
  }

  function handleDrop(event: DragEvent<HTMLDivElement>) {
    event.preventDefault();
    const nextFile = event.dataTransfer.files?.[0];
    if (nextFile) onFile(nextFile);
  }

  return (
    <section className="glass-card flex min-h-[300px] flex-col items-center justify-center border-2 border-dashed border-primary-container/30 p-glass-padding text-center transition hover:border-primary-container/60">
      <input ref={inputRef} type="file" accept="image/jpeg,image/png" className="hidden" onChange={chooseFile} />
      <div
        role="button"
        tabIndex={0}
        className="flex w-full flex-1 cursor-pointer flex-col items-center justify-center rounded-xl"
        onClick={() => inputRef.current?.click()}
        onDragOver={(event) => event.preventDefault()}
        onDrop={handleDrop}
      >
        {previewUrl ? (
          <img src={previewUrl} alt="Uploaded preview" className="max-h-[280px] w-full rounded-xl object-contain" />
        ) : (
          <>
            <h2 className="text-[24px] font-semibold leading-8 text-primary">Upload Image</h2>
            <p className="mt-2 text-[16px] leading-6 text-on-surface-variant">
              Drag and drop or click to browse
              <br />
              Supported: JPG, PNG
            </p>
          </>
        )}
      </div>

      {file ? (
        <div className="mt-5 w-full">
          <div className="flex items-center justify-between gap-4 text-left text-[14px] text-on-surface-variant">
            <span className="truncate">{file.name}</span>
            <button className="text-secondary underline-offset-4 hover:underline" onClick={() => inputRef.current?.click()}>
              Change
            </button>
          </div>
          <button className="primary-button mt-4 w-full" onClick={onInspect} disabled={isAnalyzing}>
            {isAnalyzing ? "Analyzing..." : "Run AI Inspection"}
          </button>
        </div>
      ) : null}
    </section>
  );
}

function PredictionCard({
  result,
  onFollowUpQuestion
}: {
  result: InspectionResult;
  onFollowUpQuestion?: (question: string) => void;
}) {
  if (result.kind === "non_fruit") {
    return (
      <section className="glass-card p-glass-padding">
        <p className="text-[14px] font-semibold uppercase tracking-[0.05em] text-secondary">Image check</p>
        <h2 className="mt-2 text-[24px] font-semibold text-primary">Not a fruit image</h2>
        <p className="mt-3 text-[16px] leading-6 text-on-surface-variant">{result.message}</p>
      </section>
    );
  }

  if (result.kind === "unsupported") {
    return (
      <section className="glass-card p-glass-padding">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-[14px] font-semibold uppercase tracking-[0.05em] text-secondary">Produce detected</p>
            <h2 className="mt-2 text-[28px] font-semibold leading-9 text-primary">{result.fruit_name}</h2>
          </div>
          <span className="status-pill bg-surface-container text-primary">Use Apple/Banana/Orange</span>
        </div>
        <p className="mt-5 text-[15px] leading-6 text-on-surface-variant">
          {result.message ||
            "Gemini recognised this produce, but freshness prediction is available only for Apple, Banana, and Orange right now."}
        </p>
      </section>
    );
  }

  const confidence = Math.max(0, Math.min(100, result.confidence));
  const isFresh = result.freshness_status.toLowerCase() === "fresh";
  const followUps = [
    {
      label: "Healthy recipes",
      question: `Healthy recipes with ${result.fruit_name}`
    },
    {
      label: "Calories",
      question: `${result.fruit_name} calories`
    },
    {
      label: "Desserts",
      question: `${result.fruit_name} desserts`
    }
  ];

  return (
    <section className="glass-card animate-panel-in p-glass-padding">
      <div className="flex items-start justify-between gap-4">
        <div>
          <p className="text-[14px] font-semibold uppercase tracking-[0.05em] text-secondary">AI Prediction</p>
          <h2 className="mt-2 text-[28px] font-semibold leading-9 text-primary">{result.fruit_name}</h2>
        </div>
        <span className={`status-pill ${isFresh ? "bg-emerald-100/60 text-emerald-800" : "bg-rose-100/70 text-rose-900"}`}>
          {result.freshness_status}
        </span>
      </div>

      <div className="mt-8 space-y-5">
        <MetricBar label="Confidence" value={`${confidence.toFixed(0)}%`} percent={confidence} />
        <MetricBar label="Surface Integrity" value={isFresh ? "High" : "Low"} percent={isFresh ? 85 : 38} secondary />
      </div>

      {isFresh && onFollowUpQuestion ? (
        <div className="mt-8 border-t border-outline-variant/60 pt-5">
          <p className="text-[14px] font-semibold text-secondary">Ask Prooty Assistant</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {followUps.map((item) => (
              <button
                key={item.label}
                className="followup-chip"
                type="button"
                onClick={() => onFollowUpQuestion(item.question)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
      ) : null}
    </section>
  );
}

function MetricBar({ label, value, percent, secondary = false }: { label: string; value: string; percent: number; secondary?: boolean }) {
  return (
    <div>
      <div className="mb-2 flex justify-between text-[16px]">
        <span className="text-on-surface-variant">{label}</span>
        <span className="font-semibold text-primary">{value}</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-surface-container">
        <div
          className={`h-full rounded-full ${secondary ? "bg-secondary" : "bg-primary-container"}`}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

function RecommendationTile({ label, value }: { label: string; value?: string }) {
  return (
    <div className="glass-inner flex min-h-[132px] flex-col justify-start p-5">
      <h3 className="text-[20px] font-semibold leading-7 tracking-[-0.01em] text-secondary">{label}</h3>
      <p className="mt-4 text-[18px] font-semibold leading-8 text-primary">{value || "N/A"}</p>
    </div>
  );
}

function StoragePanel({ recommendation, isUpdating = false }: { recommendation: Recommendation; isUpdating?: boolean }) {
  const isRotten = recommendation.status?.toLowerCase() === "rotten";
  const title = isRotten ? "Safety Recommendations" : "Storage Recommendations";
  const subtitle = isRotten
    ? "Gemini explains spoilage, safe handling, disposal, and prevention."
    : "Gemini explains storage, shelf life, market timing, freshness tips, and nutrition.";
  const tiles: Array<[string, string | undefined]> = isRotten
    ? [
        ["Spoilage Signs", recommendation.spoilage_signs],
        ["Possible Causes", recommendation.possible_causes],
        ["Safe Use", recommendation.safe_use],
        ["Safe Disposal", recommendation.disposal],
        ["Future Prevention", recommendation.prevention]
      ]
    : [
        ["Storage Temperature", recommendation.storage_temperature || recommendation.temperature],
        ["Storage Space", recommendation.storage_space || recommendation.storage],
        ["Shelf Life", recommendation.shelf_life],
        ["Market Sale", recommendation.market_sale || recommendation.market_recommendation],
        ["Last Longer Tip", recommendation.longevity_tip || recommendation.advice],
        ["Nutrition", recommendation.nutrition || recommendation.nutrition_highlights]
      ];

  return (
    <section className="glass-card min-h-[690px] p-glass-padding">
      <div className="flex items-start justify-between gap-5">
        <div>
          <h2 className="text-[32px] font-semibold leading-10 tracking-[-0.01em] text-primary">{title}</h2>
          <p className="mt-2 max-w-[56ch] text-[15px] leading-6 text-on-surface-variant">{subtitle}</p>
        </div>
        {isUpdating ? <span className="status-pill shrink-0 bg-surface-container text-secondary">Gemini updating</span> : null}
      </div>
      <div className="mt-8 grid grid-cols-1 gap-4 sm:grid-cols-2">
        {tiles.map(([label, value]) => <RecommendationTile label={label} value={value} key={label} />)}
      </div>
    </section>
  );
}

function AnalysisSkeleton() {
  return (
    <div className="glass-card animate-panel-in p-glass-padding">
      <div className="shimmer h-5 w-32 rounded" />
      <div className="shimmer mt-4 h-8 w-56 rounded" />
      <div className="shimmer mt-8 h-2 w-full rounded-full" />
      <div className="shimmer mt-6 h-2 w-4/5 rounded-full" />
    </div>
  );
}

function ChatLauncher({ onClick }: { onClick: () => void }) {
  return (
    <button className="chat-launcher" onClick={onClick} aria-label="Open Prooty Assistant">
      <ChatSvgIcon name="message" className="h-7 w-7 text-white" />
    </button>
  );
}

function ChatPanel({
  open,
  sessions,
  activeId,
  isSending,
  onClose,
  onCreate,
  onDelete,
  onRename,
  onSelect,
  onSend
}: {
  open: boolean;
  sessions: ChatSession[];
  activeId: string;
  isSending: boolean;
  onClose: () => void;
  onCreate: () => void;
  onDelete: (id: string) => void;
  onRename: (id: string, title: string) => void;
  onSelect: (id: string) => void;
  onSend: (text: string) => void;
}) {
  const [historyOpen, setHistoryOpen] = useState(false);
  const [draft, setDraft] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const activeSession = sessions.find((session) => session.id === activeId) || sessions[0];
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!open) return;
    bottomRef.current?.scrollIntoView({ block: "end" });
  }, [activeId, activeSession.messages.length, isSending, open]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || isSending) return;
    setDraft("");
    onSend(text);
  }

  if (!open) return null;

  return (
    <aside className="chat-panel animate-chat-in">
      <div className={`history-rail ${historyOpen ? "history-rail-open" : ""}`}>
        <div className="border-b border-white/10 p-4">
          <button className="flex w-full items-center justify-center gap-2 rounded-xl border border-white/20 px-4 py-3 text-white transition hover:bg-white/10" onClick={onCreate}>
            <ChatSvgIcon name="plus" className="h-4 w-4" />
            New Chat
          </button>
        </div>
        <div className="chat-scroll flex-1 space-y-1 overflow-y-auto p-2">
          {sessions.map((session) => (
            <div
              key={session.id}
              className={`group flex items-center gap-2 rounded-lg px-3 py-2 transition ${
                session.id === activeId ? "bg-white/10" : "hover:bg-white/10"
              }`}
            >
              <button className="flex min-w-0 flex-1 items-center gap-3 text-left" onClick={() => onSelect(session.id)}>
                <ChatSvgIcon name="message" className="h-4 w-4 shrink-0 text-white/60" />
                {editingId === session.id ? (
                  <input
                    className="w-full bg-transparent text-sm text-white outline-none"
                    defaultValue={session.title}
                    autoFocus
                    onBlur={(event) => {
                      onRename(session.id, event.target.value);
                      setEditingId(null);
                    }}
                    onKeyDown={(event) => {
                      if (event.key === "Enter") {
                        onRename(session.id, event.currentTarget.value);
                        setEditingId(null);
                      }
                    }}
                  />
                ) : (
                  <span className="truncate text-sm text-white/90">{session.title}</span>
                )}
              </button>
              <button
                className="opacity-0 transition group-hover:opacity-100"
                onClick={() => setEditingId(session.id)}
                aria-label="Rename chat"
              >
                <ChatSvgIcon name="edit" className="h-4 w-4 text-white/60" />
              </button>
              <button className="opacity-0 transition group-hover:opacity-100" onClick={() => onDelete(session.id)} aria-label="Delete chat">
                <ChatSvgIcon name="trash" className="h-4 w-4 text-white/60" />
              </button>
            </div>
          ))}
        </div>
      </div>

      <div className="flex h-full flex-col">
        <header className="flex items-center justify-between border-b border-outline-variant bg-background p-6">
          <div className="flex items-center gap-4">
            <button className="icon-button" onClick={() => setHistoryOpen((value) => !value)} aria-label="Toggle chat history">
              <ChatSvgIcon name="menu" className="h-5 w-5" />
            </button>
            <div className="flex h-10 w-10 items-center justify-center rounded-full bg-primary-container text-white">
              <ChatSvgIcon name="bot" className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-[24px] font-semibold leading-8 text-primary">Prooty Assistant</h2>
              <p className="flex items-center gap-1 text-[12px] text-secondary">
                <span className="h-2 w-2 rounded-full bg-green-500" />
                Online
              </p>
            </div>
          </div>
          <button className="icon-button" onClick={onClose} aria-label="Close chat">
            <ChatSvgIcon name="close" className="h-5 w-5" />
          </button>
        </header>

        <div className="chat-scroll flex-1 space-y-6 overflow-y-auto p-6">
          {activeSession.messages.length === 0 ? (
            <div className="mx-auto mt-14 max-w-[280px] rounded-2xl border border-outline-variant bg-white p-5 text-center text-on-surface-variant">
              Ask about fruits, storage, ripening, nutrition, shelf life, or food safety.
            </div>
          ) : (
            activeSession.messages.map((message) => <ChatBubble key={message.id} message={message} />)
          )}
          {isSending ? <TypingIndicator /> : null}
          <div ref={bottomRef} />
        </div>

        <form className="border-t border-outline-variant bg-background p-6" onSubmit={submit}>
          <div className="relative">
            <input
              className="input-hollow w-full rounded-full py-4 pl-6 pr-14 text-[16px]"
              placeholder="Ask about your fruit..."
              value={draft}
              onChange={(event) => setDraft(event.target.value)}
            />
            <button className="chat-send-button absolute right-2 top-1/2 h-10 w-10 -translate-y-1/2 rounded-full p-0" disabled={isSending} aria-label="Send message">
              <ChatSvgIcon name="send" className="h-5 w-5" />
            </button>
          </div>
          <p className="mt-3 text-center text-[12px] text-outline">Prooty Assistant can make mistakes. Verify important info.</p>
        </form>
      </div>
    </aside>
  );
}

function ChatBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={`flex w-full flex-col gap-1 ${isUser ? "items-end" : "items-start"}`}>
      <div
        className={`max-w-[88%] rounded-2xl px-5 py-3 text-[16px] leading-6 ${
          isUser
            ? "rounded-tr-sm bg-primary-container text-white"
            : "rounded-tl-sm border border-outline-variant bg-white text-on-surface shadow-sm"
        }`}
      >
        {message.content}
      </div>
      <span className="px-1 text-[12px] text-outline-variant">{message.time}</span>
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex w-20 items-center gap-1 rounded-2xl rounded-tl-sm border border-white/50 bg-white/60 px-5 py-4">
      <span className="typing-dot" />
      <span className="typing-dot delay-150" />
      <span className="typing-dot delay-300" />
    </div>
  );
}

export default function DashboardPage() {
  const [spotlightIndex, setSpotlightIndex] = useState(0);
  const [spotlightFact, setSpotlightFact] = useState(spotlightFruits[0].fallback);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [result, setResult] = useState<InspectionResult | null>(null);
  const [error, setError] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const [isSending, setIsSending] = useState(false);
  const [sessions, setSessions] = useState<ChatSession[]>(defaultSessions);
  const [activeId, setActiveId] = useState(defaultSessions[0].id);
  const [chatHydrated, setChatHydrated] = useState(false);

  const recommendation = useMemo(() => {
    if (result?.kind === "supported") return result.recommendation;
    return null;
  }, [result]);
  const pendingStorageRequest = useMemo(() => {
    if (!result || result.kind !== "supported" || !result.storage_pending) return null;
    return {
      fruitName: result.fruit_name,
      freshnessStatus: result.freshness_status
    };
  }, [result]);

  useEffect(() => {
    const stored = window.localStorage.getItem("prootypie-chat");
    if (stored) {
      try {
        const parsed = JSON.parse(stored) as { sessions: ChatSession[]; activeId: string };
        if (parsed.sessions?.length) {
          setSessions(parsed.sessions);
          setActiveId(parsed.activeId || parsed.sessions[0].id);
        }
      } catch {
        setSessions(defaultSessions);
        setActiveId(defaultSessions[0].id);
      }
    }
    setChatHydrated(true);
  }, []);

  useEffect(() => {
    if (!chatHydrated) return;
    window.localStorage.setItem("prootypie-chat", JSON.stringify({ sessions, activeId }));
  }, [activeId, chatHydrated, sessions]);

  useEffect(() => {
    const fruit = spotlightFruits[spotlightIndex];
    let cancelled = false;
    getSpotlightFact(fruit.name)
      .then((fact) => {
        if (!cancelled) setSpotlightFact(fact);
      })
      .catch(() => {
        if (!cancelled) setSpotlightFact(fruit.fallback);
      });
    return () => {
      cancelled = true;
    };
  }, [spotlightIndex]);

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  useEffect(() => {
    if (!pendingStorageRequest) return;

    let cancelled = false;
    const { fruitName, freshnessStatus } = pendingStorageRequest;

    fetchStorageRecommendation(fruitName, freshnessStatus)
      .then((recommendation) => {
        if (cancelled) return;
        setResult((current) => {
          if (!current || current.kind !== "supported" || current.fruit_name !== fruitName) return current;
          if (current.freshness_status !== freshnessStatus) return current;
          return {
            ...current,
            recommendation,
            recommendation_source: "gemini",
            storage_pending: false
          };
        });
      })
      .catch(() => {
        if (cancelled) return;
        setResult((current) => {
          if (!current || current.kind !== "supported" || current.fruit_name !== fruitName) return current;
          return { ...current, storage_pending: false };
        });
      });

    return () => {
      cancelled = true;
    };
  }, [pendingStorageRequest]);

  function handleFile(nextFile: File) {
    setError("");
    setResult(null);
    setFile(nextFile);
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(URL.createObjectURL(nextFile));
  }

  async function handleInspect() {
    if (!file) return;
    setError("");
    setResult(null);
    setIsAnalyzing(true);
    try {
      const nextResult = await inspectImage(file);
      setResult(nextResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Inspection failed. Please try again.");
    } finally {
      setIsAnalyzing(false);
    }
  }

  function createChat() {
    const session: ChatSession = { id: makeId(), title: "New chat", messages: [] };
    setSessions((current) => [session, ...current]);
    setActiveId(session.id);
  }

  function deleteChat(id: string) {
    setSessions((current) => {
      const remaining = current.filter((session) => session.id !== id);
      if (remaining.length === 0) {
        setActiveId(defaultSessions[0].id);
        return defaultSessions;
      }
      if (activeId === id) setActiveId(remaining[0].id);
      return remaining;
    });
  }

  function renameChat(id: string, title: string) {
    setSessions((current) =>
      current.map((session) => (session.id === id ? { ...session, title: title.trim() || "New chat" } : session))
    );
  }

  async function handleSend(text: string) {
    const targetId = activeId;
    const currentSession = sessions.find((session) => session.id === targetId) || defaultSessions[0];
    const userMessage: ChatMessage = { id: makeId(), role: "user", content: text, time: timeLabel() };
    const outgoing: ChatMessage[] = [...currentSession.messages, userMessage];

    setSessions((current) =>
      current.map((session) => {
        if (session.id !== targetId) return session;
        const nextTitle = session.title === "New chat" ? text.split(/\s+/).slice(0, 5).join(" ") : session.title;
        return { ...session, title: nextTitle, messages: outgoing };
      })
    );

    setIsSending(true);
    try {
      const reply = await sendChat(outgoing);
      const assistantMessage: ChatMessage = { id: makeId(), role: "assistant", content: reply, time: timeLabel() };
      setSessions((current) =>
        current.map((session) =>
          session.id === targetId ? { ...session, messages: [...session.messages, assistantMessage] } : session
        )
      );
    } catch (err) {
      const assistantMessage: ChatMessage = {
        id: makeId(),
        role: "assistant",
        content: err instanceof Error ? err.message : "I'm having trouble connecting right now. Please try again in a moment.",
        time: timeLabel()
      };
      setSessions((current) =>
        current.map((session) =>
          session.id === targetId ? { ...session, messages: [...session.messages, assistantMessage] } : session
        )
      );
    } finally {
      setIsSending(false);
    }
  }

  function handleFollowUpQuestion(question: string) {
    if (isSending) return;
    setChatOpen(true);
    void handleSend(question);
  }

  return (
    <AppShell>
      <Sidebar
        spotlightIndex={spotlightIndex}
        spotlightFact={spotlightFact}
        onNext={() => setSpotlightIndex((current) => (current + 1) % spotlightFruits.length)}
      />
      <div className="min-h-screen md:pl-72">
        <Header />
        <div className="mx-auto w-full max-w-[1440px] px-margin-mobile pb-margin-desktop md:px-margin-desktop">
          <div className={recommendation ? "grid gap-gutter lg:grid-cols-12" : "max-w-[430px]"}>
            <div className={recommendation ? "flex flex-col gap-gutter lg:col-span-5" : "flex flex-col gap-gutter"}>
              <UploadDropzone file={file} previewUrl={previewUrl} isAnalyzing={isAnalyzing} onFile={handleFile} onInspect={handleInspect} />
              {isAnalyzing ? <AnalysisSkeleton /> : null}
              {result ? <PredictionCard result={result} onFollowUpQuestion={handleFollowUpQuestion} /> : null}
              {error ? (
                <div className="glass-card p-5 text-[16px] leading-6 text-primary">
                  <strong>Inspection failed:</strong> {error}
                </div>
              ) : null}
            </div>
            {recommendation ? (
              <div className="lg:col-span-7">
                <StoragePanel recommendation={recommendation} isUpdating={Boolean(result?.kind === "supported" && result.storage_pending)} />
              </div>
            ) : null}
          </div>
        </div>
      </div>
      <ChatLauncher onClick={() => setChatOpen(true)} />
      <ChatPanel
        open={chatOpen}
        sessions={sessions}
        activeId={activeId}
        isSending={isSending}
        onClose={() => setChatOpen(false)}
        onCreate={createChat}
        onDelete={deleteChat}
        onRename={renameChat}
        onSelect={setActiveId}
        onSend={handleSend}
      />
    </AppShell>
  );
}
