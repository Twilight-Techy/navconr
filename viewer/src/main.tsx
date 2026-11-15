import React, { useEffect, useMemo, useState, useRef } from "react";
import { createRoot } from "react-dom/client";
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
  type ReactFlowInstance,
} from "@xyflow/react";
import {
  ArrowDownRight,
  ArrowUpRight,
  Check,
  ChevronDown,
  ChevronRight,
  CircleDot,
  Code2,
  Database,
  FileText,
  FolderTree,
  GitBranch,
  Layers,
  LoaderCircle,
  Play,
  Search,
  Terminal,
  X,
} from "lucide-react";
import "@xyflow/react/dist/style.css";
import "./style.css";

type Card = {
  id: string;
  title: string;
  summary: string;
  kind: string;
  children: number;
  span_ids: string[];
  source: string | null;
  score?: number;
  parent?: string | null;
};
type Page = {
  schema_version: number;
  revision: string;
  items: Card[];
  next_cursor: string | null;
  unresolved: string[];
};
type Span = {
  id: string;
  source: string;
  start: number;
  end: number;
  line_start: number;
  line_end: number;
  coordinate: string;
  origin?: string;
};
type Evidence = { span: Span; text: string; revision: string };
type Usage = {
  steps: number;
  source_bytes: number;
  map_bytes: number;
  model_calls: number;
  model_tokens: number;
};
type Run = {
  run_id: string;
  revision: string;
  query: string;
  policy?: string;
  stop_reason: string;
  usage: Usage;
};
type Event = {
  sequence: number;
  action: string;
  arguments: Record<string, unknown>;
  response: Record<string, unknown>;
  elapsed_ms: number;
  usage: Usage;
};
type RunPage = Run & {
  schema_version: number;
  trace: Event[];
  next_offset: number | null;
  evidence: Span[];
};
type Status = {
  schema_version: number;
  revision: string;
  sources: number;
  nodes: number;
  spans: number;
  diagnostics: string[];
};

async function api<T>(
  route: string,
  args: Record<string, string> = {},
): Promise<T> {
  const response = await fetch(
    "/api/" + route + "?" + new URLSearchParams(args),
  );
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || "Request failed");
  if (body.schema_version && body.schema_version !== 1)
    throw new Error("Unsupported export version. Update the inspector.");
  return body as T;
}

function App() {
  const flow = useRef<ReactFlowInstance | null>(null);
  const selectionRequest = useRef(0);
  const [mapView, setMapView] = useState("physical");
  const [relation, setRelation] = useState("reference");
  const [edgeOrigin, setEdgeOrigin] = useState("all");
  const [status, setStatus] = useState<Status>();
  const [cards, setCards] = useState<Record<string, Card>>({});
  const [parents, setParents] = useState<Record<string, string>>({});
  const [roots, setRoots] = useState<string[]>([]);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [cursor, setCursor] = useState<string | null>(null);
  const [childCursors, setChildCursors] = useState<
    Record<string, string | null>
  >({});
  const [selected, setSelected] = useState<string | null>(null);
  const [evidence, setEvidence] = useState<Evidence[]>([]);
  const [related, setRelated] = useState<Card[]>([]);
  const [unresolved, setUnresolved] = useState<string[]>([]);
  const [references, setReferences] = useState<Edge[]>([]);
  const [showReferences, setShowReferences] = useState(true);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<Card[] | null>(null);
  const [searchCursor, setSearchCursor] = useState<string | null>(null);
  const [runs, setRuns] = useState<Run[]>([]);
  const [run, setRun] = useState<RunPage>();
  const [eventIndex, setEventIndex] = useState(0);
  const [tab, setTab] = useState<"map" | "trace">("map");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [copied, setCopied] = useState(false);

  async function work(operation: () => Promise<void>) {
    setBusy(true);
    setError("");
    try {
      await operation();
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  function merge(items: Card[], parent?: string) {
    setCards((previous) => ({
      ...previous,
      ...Object.fromEntries(items.map((card) => [card.id, card])),
    }));
    if (parent)
      setParents((previous) => ({
        ...previous,
        ...Object.fromEntries(items.map((card) => [card.id, parent])),
      }));
  }

  useEffect(() => {
    void work(async () => {
      const info = await api<Status>("status");
      setStatus(info);
      const overview = await api<Page>("overview");
      merge(overview.items, "root");
      setRoots(overview.items.map((card) => card.id));
      setCursor(overview.next_cursor);
      const history = await api<{ items: Run[] }>("runs");
      setRuns(history.items);
    });
  }, []);

  const revisionArgs: Record<string, string> =
    tab === "trace" && run
      ? { revision: run.revision }
      : status
        ? { revision: status.revision }
        : {};

  async function expand(card: Card, continuation?: string) {
    const page = await api<Page>("expand", {
      ids: card.id,
      ...revisionArgs,
      ...(continuation ? { cursor: continuation } : {}),
    });
    merge(page.items, card.id);
    setExpanded((old) => new Set([...old, card.id]));
    setChildCursors((old) => ({ ...old, [card.id]: page.next_cursor }));
  }

  async function select(card: Card) {
    const requestId = ++selectionRequest.current;
    setSelected(card.id);
    setEvidence([]);
    setRelated([]);
    setUnresolved([]);
    if (card.span_ids.length) {
      const response = await api<{
        items: { evidence?: Evidence; error?: string }[];
      }>("read", {
        ids: card.span_ids.slice(0, 20).join(","),
        ...revisionArgs,
      });
      if (requestId !== selectionRequest.current) return;
      setEvidence(
        response.items.flatMap((item) =>
          item.evidence ? [item.evidence] : [],
        ),
      );
      const failures = response.items
        .filter((item) => item.error)
        .map((item) => item.error)
        .join("; ");
      if (failures) setError(failures);
    }
    const linked = await api<Page>("follow", {
      id: card.id,
      relation,
      ...(edgeOrigin === "all" ? {} : { origin: edgeOrigin }),
      ...revisionArgs,
    });
    if (requestId !== selectionRequest.current) return;
    setRelated(linked.items);
    setUnresolved(linked.unresolved);
    merge(linked.items);
    setReferences((old) => {
      const map = new Map(old.map((edge) => [edge.id, edge]));
      linked.items.forEach((target) =>
        map.set(card.id + target.id, {
          id: card.id + target.id,
          source: card.id,
          target: target.id,
          label: relation,
          animated: true,
          style: { stroke: "#cf744f" },
        }),
      );
      return [...map.values()];
    });
  }

  function choose(card: Card) {
    void work(async () => {
      await select(card);
      if (card.children && !expanded.has(card.id)) await expand(card);
    });
  }

  async function search(continuation?: string) {
    if (!query.trim()) {
      setResults(null);
      setSearchCursor(null);
      return;
    }
    const page = await api<Page>("search", {
      q: query,
      ...revisionArgs,
      ...(continuation ? { cursor: continuation } : {}),
    });
    merge(page.items);
    setResults((old) =>
      continuation ? [...(old || []), ...page.items] : page.items,
    );
    setSearchCursor(page.next_cursor);
  }

  async function changeView(view: string) {
    selectionRequest.current++;
    setMapView(view);
    setSelected(null);
    setEvidence([]);
    setRelated([]);
    setResults(null);
    setExpanded(new Set());
    const page = await api<Page>("overview", { view, ...revisionArgs });
    merge(page.items, "root");
    setRoots(page.items.map((card) => card.id));
    setCursor(page.next_cursor);
  }

  useEffect(() => {
    if (selected && cards[selected]) void work(() => select(cards[selected]));
  }, [relation, edgeOrigin]);

  async function loadRun(id: string, nextOffset?: number) {
    const page = await api<RunPage>("run", {
      id,
      ...(nextOffset ? { offset: String(nextOffset) } : {}),
    });
    setRun((old) =>
      nextOffset && old
        ? { ...page, trace: [...old.trace, ...page.trace] }
        : page,
    );
    const observed = page.trace.flatMap((event) =>
      Array.isArray(event.response.items)
        ? event.response.items.filter(
            (item): item is Card =>
              !!item &&
              typeof item === "object" &&
              "kind" in item &&
              "id" in item,
          )
        : [],
    );
    merge(observed);
    const observedParents = Object.fromEntries(
      observed
        .filter((card) => card.parent)
        .map((card) => [card.id, card.parent!]),
    );
    setParents((old) => ({ ...old, ...observedParents }));
    setRoots((old) => [
      ...new Set([
        ...old,
        ...observed
          .filter((card) => card.parent === "root")
          .map((card) => card.id),
      ]),
    ]);
    setExpanded((old) => new Set([...old, ...Object.values(observedParents)]));
    if (!nextOffset) setEventIndex(0);
  }

  const graph = useMemo(() => {
    const visible = new Set<string>(["root", ...roots]);
    const addChildren = (id: string) => {
      if (!expanded.has(id)) return;
      Object.keys(parents)
        .filter((key) => parents[key] === id)
        .forEach((key) => {
          visible.add(key);
          addChildren(key);
        });
    };
    roots.forEach(addChildren);
    results?.forEach((card) => visible.add(card.id));
    if (selected) visible.add(selected);
    if (showReferences) related.forEach((card) => visible.add(card.id));
    const nodes: Node[] = [];
    const edges: Edge[] = [];
    const rows: Record<number, number> = {};
    const activeEvent = run?.trace[eventIndex];
    const highlighted = new Set<string>(
      Object.values(activeEvent?.arguments || {}).flatMap((value) =>
        Array.isArray(value)
          ? value.filter((v) => typeof v === "string")
          : typeof value === "string"
            ? [value]
            : [],
      ),
    );
    for (const id of visible) {
      let depth = 0;
      let parent = parents[id];
      const seen = new Set([id]);
      while (parent && !seen.has(parent)) {
        depth++;
        seen.add(parent);
        parent = parents[parent];
      }
      const row = rows[depth] || 0;
      rows[depth] = row + 1;
      const card = cards[id];
      nodes.push({
        id,
        position: { x: depth * 250, y: row * 122 },
        data: {
          label: (
            <div className="graph-card">
              <span className="node-kind">
                {id === "root" ? "KNOWLEDGE MAP" : card?.kind.toUpperCase()}
              </span>
              <strong>
                {id === "root" ? "Collection overview" : card?.title}
              </strong>
              <span>
                {id === "root"
                  ? `${status?.sources || 0} sources`
                  : `${card?.children || 0} children · ${card?.span_ids.length || 0} spans`}
              </span>
            </div>
          ),
        },
        selected: selected === id,
        style: {
          width: 204,
          borderColor: highlighted.has(id)
            ? "#cb724f"
            : selected === id
              ? "#256f61"
              : "#dce1dc",
        },
      });
      if (parents[id] && visible.has(parents[id]))
        edges.push({
          id: "p-" + id,
          source: parents[id],
          target: id,
          style: { stroke: "#b9c8c0" },
        });
    }
    if (showReferences)
      edges.push(
        ...references.filter(
          (edge) => visible.has(edge.source) && visible.has(edge.target),
        ),
      );
    return { nodes, edges };
  }, [
    cards,
    parents,
    roots,
    expanded,
    selected,
    results,
    related,
    references,
    showReferences,
    status,
    run,
    eventIndex,
  ]);

  useEffect(() => {
    const timer = setTimeout(() => {
      void flow.current?.fitView({ padding: 0.18, duration: 200, maxZoom: 1 });
    }, 70);
    return () => clearTimeout(timer);
  }, [graph.nodes.length, tab]);

  function tree(id: string, depth = 0): React.ReactNode {
    const card = cards[id];
    if (!card) return null;
    const children = Object.keys(parents).filter((key) => parents[key] === id);
    return (
      <React.Fragment key={id}>
        <button
          className={"tree-row " + (selected === id ? "active" : "")}
          style={{ paddingLeft: 16 + depth * 15 }}
          onClick={() => choose(card)}
          title={card.title}
        >
          {card.children ? (
            expanded.has(id) ? (
              <ChevronDown size={13} />
            ) : (
              <ChevronRight size={13} />
            )
          ) : (
            <span className="tree-dot" />
          )}
          {card.kind === "document" ? (
            <FileText size={15} />
          ) : (
            <CircleDot size={13} />
          )}
          <span>{card.title}</span>
        </button>
        {expanded.has(id) && (
          <>
            {children.map((child) => tree(child, depth + 1))}
            {childCursors[id] && (
              <button
                className="load-more"
                onClick={() =>
                  void work(() => expand(card, childCursors[id] || undefined))
                }
              >
                Load more children
              </button>
            )}
          </>
        )}
      </React.Fragment>
    );
  }

  const current = selected ? cards[selected] : null;
  const activeEvent = run?.trace[eventIndex];

  return (
    <div className="app">
      <aside className="rail">
        <div className="brand-mark">
          <Layers size={23} />
        </div>
        <button
          className={tab === "map" ? "rail-button active" : "rail-button"}
          aria-label="Knowledge map"
          title="Knowledge map"
          onClick={() => setTab("map")}
        >
          <FolderTree size={20} />
        </button>
        <button
          className={tab === "trace" ? "rail-button active" : "rail-button"}
          aria-label="Retrieval traces"
          title="Retrieval traces"
          onClick={() => setTab("trace")}
        >
          <GitBranch size={20} />
        </button>
        <div className="rail-bottom">
          <Code2 size={19} />
          <span>RC1</span>
        </div>
      </aside>
      <main>
        <header>
          <div>
            <span className="eyebrow">NAVCONR / WORKSPACE</span>
            <h1>
              Knowledge inspector
              <span className="local-badge">
                <span />
                Local
              </span>
            </h1>
          </div>
          <div className="header-right">
            <span className="version">v0.1.0-rc.1</span>
            <button
              className="quiet-button"
              onClick={() => {
                void navigator.clipboard
                  ?.writeText(status?.revision || "")
                  .then(() => {
                    setCopied(true);
                    setTimeout(() => setCopied(false), 1500);
                  });
              }}
            >
              {copied ? <Check size={14} /> : <Database size={14} />}{" "}
              {status?.revision.slice(0, 8) || "Connecting"}
            </button>
          </div>
        </header>
        <div className="intro">
          <div>
            <h2>
              {tab === "map"
                ? "A map before the details."
                : "Follow the evidence."}
            </h2>
            <p>
              {tab === "map"
                ? "Explore the structure. Follow a connection. Read the original source."
                : "Replay recorded actions and inspect what each retrieval actually returned."}
            </p>
          </div>
          <span className="integrity">
            <span />
            Immutable sources · Exact spans
          </span>
        </div>
        <div className="stats">
          <div>
            <FileText size={17} />
            <strong>{status?.sources ?? "—"}</strong>
            <span>sources</span>
          </div>
          <div>
            <FolderTree size={17} />
            <strong>{status?.nodes ?? "—"}</strong>
            <span>navigation nodes</span>
          </div>
          <div>
            <ArrowDownRight size={17} />
            <strong>{status?.spans ?? "—"}</strong>
            <span>source spans</span>
          </div>
          <div>
            <GitBranch size={17} />
            <strong>{runs.length}</strong>
            <span>recent traces</span>
          </div>
        </div>
        {error && (
          <div className="error" role="alert">
            {error}
            <button aria-label="Dismiss error" onClick={() => setError("")}>
              <X size={15} />
            </button>
          </div>
        )}
        <div className="workspace">
          <section className="outline panel">
            <div className="panel-heading">
              <h3>{tab === "map" ? "Collection" : "Retrieval history"}</h3>
              <span className="small-count">
                {tab === "map" ? status?.sources : runs.length}
              </span>
            </div>
            {tab === "map" ? (
              <>
                <form
                  className="search"
                  onSubmit={(event) => {
                    event.preventDefault();
                    void work(() => search());
                  }}
                >
                  <Search size={15} />
                  <input
                    aria-label="Search knowledge"
                    value={query}
                    onChange={(event) => setQuery(event.target.value)}
                    placeholder="Find a topic or phrase…"
                  />
                  <button aria-label="Run search">
                    <ArrowUpRight size={16} />
                  </button>
                </form>
                <div className="tree-scroll">
                  {results ? (
                    <>
                      <div className="list-caption">
                        SEARCH RESULTS{" "}
                        <button
                          onClick={() => {
                            setResults(null);
                            setQuery("");
                          }}
                        >
                          Clear
                        </button>
                      </div>
                      {results.map((card) => (
                        <button
                          key={card.id}
                          className={
                            "result-row " +
                            (selected === card.id ? "active" : "")
                          }
                          onClick={() => choose(card)}
                        >
                          <FileText size={14} />
                          <span>
                            <strong>{card.title}</strong>
                            <small>{card.source}</small>
                          </span>
                        </button>
                      ))}
                      {results.length === 0 && (
                        <p className="empty-text">
                          No matching source entries.
                        </p>
                      )}
                      {searchCursor && (
                        <button
                          className="load-more"
                          onClick={() => void work(() => search(searchCursor))}
                        >
                          More results
                        </button>
                      )}
                    </>
                  ) : (
                    <>
                      <div className="list-caption">
                        <select
                          aria-label="Map organization"
                          value={mapView}
                          onChange={(event) =>
                            void work(() => changeView(event.target.value))
                          }
                        >
                          <option value="physical">Source structure</option>
                          <option value="semantic">Topic maps</option>
                        </select>
                      </div>
                      {roots.map((id) => tree(id))}
                      {cursor && (
                        <button
                          className="load-more"
                          onClick={() =>
                            void work(async () => {
                              const page = await api<Page>("overview", {
                                cursor,
                                view: mapView,
                                ...revisionArgs,
                              });
                              merge(page.items, "root");
                              setRoots((old) => [
                                ...old,
                                ...page.items.map((c) => c.id),
                              ]);
                              setCursor(page.next_cursor);
                            })
                          }
                        >
                          Load more sources
                        </button>
                      )}
                    </>
                  )}
                </div>
                <div className="outline-foot">
                  <span className="tiny-dot" />
                  {Object.keys(cards).length} nodes loaded · bounded views
                </div>
              </>
            ) : (
              <div className="tree-scroll">
                {runs.length ? (
                  runs.map((item) => (
                    <button
                      key={item.run_id}
                      className={
                        "run-row " +
                        (run?.run_id === item.run_id ? "active" : "")
                      }
                      onClick={() => void work(() => loadRun(item.run_id))}
                    >
                      <GitBranch size={15} />
                      <span>
                        <strong>{item.query}</strong>
                        <small>
                          {item.policy} ·{" "}
                          {item.stop_reason.replaceAll("_", " ")}
                        </small>
                      </span>
                    </button>
                  ))
                ) : (
                  <div className="empty-state">
                    <Terminal />
                    <p>No recorded retrievals.</p>
                    <code>navconr query "your question"</code>
                  </div>
                )}
              </div>
            )}
          </section>
          <section className="canvas panel">
            <div className="panel-heading">
              <h3>
                <GitBranch size={15} />
                {tab === "map" ? "Navigation map" : "Recorded path"}
              </h3>
              <label className="toggle">
                <input
                  type="checkbox"
                  checked={showReferences}
                  onChange={(event) => setShowReferences(event.target.checked)}
                />
                References
              </label>
            </div>
            <div className="flow">
              <ReactFlow
                onInit={(instance) => {
                  flow.current = instance;
                }}
                nodes={graph.nodes}
                edges={graph.edges}
                onNodeClick={(_, node) => {
                  if (cards[node.id]) choose(cards[node.id]);
                }}
                fitView
                fitViewOptions={{ padding: 0.25 }}
                minZoom={0.2}
                maxZoom={1.8}
                nodesDraggable={false}
              >
                <Background color="#d7ded8" gap={22} size={1} />
                <Controls showInteractive={false} />
                <MiniMap pannable zoomable nodeColor="#d3e4da" />
              </ReactFlow>
              {!status && (
                <div className="loading">
                  <LoaderCircle className="spin" size={20} />
                  Connecting to local index…
                </div>
              )}
            </div>
            <div className="canvas-foot">
              <span>
                <i className="legend physical" />
                Source hierarchy
              </span>
              <span>
                <i className="legend reference" />
                Explicit reference
              </span>
              <span className="canvas-hint">Select a node to inspect</span>
            </div>
            {tab === "trace" && run && (
              <div className="trace-player">
                <div className="trace-meta">
                  <strong>{run.query}</strong>
                  <span>
                    {run.stop_reason.replaceAll("_", " ")} ·{" "}
                    {run.usage.source_bytes} source bytes
                  </span>
                </div>
                <div className="trace-controls">
                  <button
                    aria-label="Next recorded action"
                    onClick={() =>
                      setEventIndex((index) =>
                        Math.min(index + 1, run.trace.length - 1),
                      )
                    }
                  >
                    <Play size={15} />
                  </button>
                  <input
                    aria-label="Recorded action"
                    type="range"
                    min="0"
                    max={Math.max(0, run.trace.length - 1)}
                    value={eventIndex}
                    onChange={(event) =>
                      setEventIndex(Number(event.target.value))
                    }
                  />
                  <span>
                    {eventIndex + 1}/{run.trace.length}
                  </span>
                </div>
                {activeEvent && (
                  <div className="event">
                    <span className="event-action">{activeEvent.action}</span>
                    <span>{activeEvent.elapsed_ms.toFixed(1)} ms</span>
                    <span>
                      {activeEvent.usage.steps} steps ·{" "}
                      {activeEvent.usage.source_bytes} bytes
                    </span>
                  </div>
                )}
                {run.next_offset !== null && (
                  <button
                    className="load-more"
                    onClick={() =>
                      void work(() =>
                        loadRun(run.run_id, run.next_offset || undefined),
                      )
                    }
                  >
                    Load more recorded actions
                  </button>
                )}
              </div>
            )}
          </section>
          <section className="inspector panel">
            <div className="panel-heading">
              <h3>
                <FileText size={15} />
                Source inspector
              </h3>
              {busy && <LoaderCircle className="spin" size={15} />}
            </div>
            {current ? (
              <div className="inspector-scroll">
                <div className="selected-info">
                  <span className="tag">{current.kind}</span>
                  <h3>{current.title}</h3>
                  <p className="source-path">
                    {current.source || "Collection map"}
                  </p>
                </div>
                <div className="relationship-filters">
                  <label>
                    Relationship
                    <select
                      aria-label="Relationship type"
                      value={relation}
                      onChange={(event) => setRelation(event.target.value)}
                    >
                      <option value="reference">References</option>
                      <option value="member">Topic members</option>
                      <option value="related">Related entries</option>
                      <option value="imports">Imports</option>
                    </select>
                  </label>
                  <label>
                    Origin
                    <select
                      aria-label="Relationship origin"
                      value={edgeOrigin}
                      onChange={(event) => setEdgeOrigin(event.target.value)}
                    >
                      <option value="all">All origins</option>
                      <option value="parsed">Parsed</option>
                      <option value="manual">Manual</option>
                      <option value="similarity">Similarity</option>
                      <option value="inferred">Inferred</option>
                    </select>
                  </label>
                </div>
                <div className="detail-label">NAVIGATION SUMMARY</div>
                <p className="summary">
                  {current.summary || "No summary for this entry."}
                </p>
                <div className="detail-label">
                  ORIGINAL EVIDENCE <span>{evidence.length}</span>
                </div>
                {evidence.length ? (
                  evidence.map((item) => (
                    <div className="evidence" key={item.span.id}>
                      <div className="evidence-heading">
                        <span>
                          {item.span.coordinate === "original"
                            ? "Original text"
                            : item.span.origin || "Extracted text"}
                        </span>
                        <span>
                          L{item.span.line_start}–{item.span.line_end}
                        </span>
                      </div>
                      <pre>{item.text}</pre>
                      <div className="evidence-footer">
                        bytes {item.span.start}–{item.span.end} ·{" "}
                        {item.revision.slice(0, 8)}
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="empty-text">
                    Expand this entry and select a source block to read its
                    exact text.
                  </p>
                )}
                {related.length > 0 && (
                  <>
                    <div className="detail-label">
                      CONNECTED ENTRIES · {edgeOrigin.toUpperCase()}
                    </div>
                    {related.map((card) => (
                      <button
                        className="related"
                        key={card.id}
                        onClick={() => choose(card)}
                      >
                        <ArrowUpRight size={14} />
                        {card.title}
                      </button>
                    ))}
                  </>
                )}
                {unresolved.length > 0 && (
                  <>
                    <div className="detail-label">UNRESOLVED REFERENCES</div>
                    {unresolved.map((link, index) => (
                      <p className="empty-text" key={index}>
                        {link}
                      </p>
                    ))}
                  </>
                )}
                {current.children > 0 && (
                  <button
                    className="primary"
                    onClick={() => void work(() => expand(current))}
                  >
                    <Layers size={15} />
                    Expand entry
                    <ChevronRight size={15} />
                  </button>
                )}
              </div>
            ) : (
              <div className="empty-state inspector-empty">
                <div className="empty-icon">
                  <FileText size={24} />
                </div>
                <h3>Details, when you need them.</h3>
                <p>
                  Select any node to inspect its summary, source locations, and
                  connected references.
                </p>
                <span>Every passage stays anchored to its source.</span>
              </div>
            )}
          </section>
        </div>
        <footer>
          <span>
            <span className="tiny-dot" />
            {status ? "Connected to local index" : "Waiting for index"}
          </span>
          <span>Maps guide navigation. Sources provide evidence.</span>
        </footer>
      </main>
    </div>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
