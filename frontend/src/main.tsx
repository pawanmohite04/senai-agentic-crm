import React, { useEffect, useMemo, useState } from "react";
import { createRoot } from "react-dom/client";
import { AlertTriangle, BarChart3, Inbox, RefreshCw, Search, ShieldCheck, UserRound } from "lucide-react";
import { Bar, BarChart, CartesianGrid, Cell, Line, LineChart, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { getJson, postJson } from "./lib/api";
import "./styles.css";

type Stats = { pending: number; replied: number; escalated: number; critical: number; spam_filtered: number };
type Category = { category: string; count: number };
type Point = { timestamp: string; sender: string; sentiment_score: number };
type ThreadEmail = { id: number; message_id: string; subject: string; body: string; timestamp: string; sentiment_score: number; category: string; urgency: string; requires_human: boolean; actions: Array<{ id: number; action_type: string; proposed_content: string; reasoning: any }> };
type ThreadResponse = { contact: any; threads: Array<{ thread_id: string; subject: string; status: string; emails: ThreadEmail[] }> };

const contacts = [
  "bob.jones@enterprise.net",
  "karen.w@retail-co.com",
  "marcus.del@fintech-startup.co",
  "hacker@anon-collective.net",
  "alice.smith@greenlight-npo.org",
  "nadia.k@global-logistics.com",
  "procurement@bigcorp-global.com",
  "eleanor.voss@healthcare-group.org"
];

function Badge({ value }: { value: string }) {
  const tone = value === "Critical" || value === "Legal" ? "danger" : value === "High" || value === "Escalated" ? "warn" : value === "Spam" ? "muted" : "ok";
  return <span className={`badge ${tone}`}>{value}</span>;
}

function App() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [cats, setCats] = useState<Category[]>([]);
  const [trend, setTrend] = useState<Point[]>([]);
  const [selected, setSelected] = useState(contacts[0]);
  const [thread, setThread] = useState<ThreadResponse | null>(null);
  const [rag, setRag] = useState<any>(null);
  const [intel, setIntel] = useState<any>(null);
  const [query, setQuery] = useState("SLA legal renewal hold");

  async function load() {
    setStats(await getJson<Stats>("/dashboard/stats"));
    setCats((await getJson<{ categories: Category[] }>("/analytics/category-breakdown")).categories);
    setTrend((await getJson<{ points: Point[] }>("/analytics/sentiment-trend")).points);
    setThread(await getJson<ThreadResponse>(`/threads/${selected}`));
    setRag(await getJson(`/rag/search?q=${encodeURIComponent(query)}`));
    setIntel(await getJson("/intelligence/reputation"));
  }

  useEffect(() => { load().catch(console.error); }, [selected]);

  const emails = useMemo(() => thread?.threads.flatMap(t => t.emails.map(e => ({ ...e, thread_id: t.thread_id }))) || [], [thread]);
  const allActions = emails.flatMap(e => e.actions);
  const latestAction = allActions.length ? allActions[allActions.length - 1] : undefined;

  return (
    <main>
      <header>
        <div>
          <h1>SenAI Mission Control</h1>
          <p>Agentic CRM operations, escalation safety, RAG evidence, and account intelligence.</p>
        </div>
        <button onClick={load}><RefreshCw size={16} /> Refresh</button>
      </header>

      <section className="stats">
        {stats && Object.entries(stats).map(([key, value]) => <div className="metric" key={key}><span>{key.replace("_", " ")}</span><strong>{value}</strong></div>)}
      </section>

      <section className="layout">
        <aside>
          <div className="section-title"><Inbox size={16} /> Mission Control Inbox</div>
          <div className="tabs"><button>All</button><button>Needs Human</button><button>Escalated</button><button>Spam</button></div>
          <label className="search"><Search size={15} /><input value={selected} onChange={e => setSelected(e.target.value)} /></label>
          <div className="contact-list">
            {contacts.map(c => <button className={c === selected ? "active" : ""} onClick={() => setSelected(c)} key={c}><UserRound size={14} />{c}</button>)}
          </div>
          <div className="bulk"><button>Mark Spam</button><button>Assign</button><button>Archive</button></div>
        </aside>

        <section className="workspace">
          <div className="section-title"><ShieldCheck size={16} /> Thread Workspace</div>
          {thread && <div className="profile">
            <strong>{thread.contact.name}</strong><span>{thread.contact.company}</span><Badge value={thread.contact.status} />
          </div>}
          <div className="timeline">
            {emails.map(e => <article key={e.id}>
              <div className="email-head"><strong>{e.subject}</strong><span>{new Date(e.timestamp).toLocaleString()}</span></div>
              <p>{e.body}</p>
              <div className="badges"><Badge value={e.category} /><Badge value={e.urgency} /><Badge value={`sentiment ${e.sentiment_score}`} /></div>
            </article>)}
          </div>
        </section>

        <aside>
          <div className="section-title"><AlertTriangle size={16} /> Agent Reasoning</div>
          <div className="panel">
            {latestAction?.reasoning?.trace?.map((step: any, idx: number) => <div className="trace" key={idx}>
              <strong>Thought</strong><p>{step.thought}</p><strong>Action</strong><p>{step.action}</p><strong>Observation</strong><p>{typeof step.observation === "string" ? step.observation : JSON.stringify(step.observation)}</p><strong>Next Step</strong><p>{step.next_step}</p>
            </div>) || "No reasoning trace loaded."}
          </div>
          <div className="section-title">RAG Context</div>
          <label className="search"><Search size={15} /><input value={query} onChange={e => setQuery(e.target.value)} onBlur={load} /></label>
          <div className="panel">{rag?.results?.map((r: any) => <p key={r.id}><strong>{r.source_doc}</strong> {r.score}: {r.chunk_text.slice(0, 170)}...</p>)}</div>
          <div className="section-title">Web Intelligence</div>
          <div className="panel"><pre>{JSON.stringify(intel, null, 2)}</pre></div>
        </aside>
      </section>

      <section className="analytics">
        <div className="section-title"><BarChart3 size={16} /> Analytics Dashboard</div>
        <div className="charts">
          <div>
            <h2>Sentiment Trend</h2>
            <ResponsiveContainer height={220}><LineChart data={trend}><CartesianGrid /><XAxis dataKey="timestamp" hide /><YAxis domain={[-1, 1]} /><Tooltip /><Line dataKey="sentiment_score" stroke="#0f766e" /></LineChart></ResponsiveContainer>
          </div>
          <div>
            <h2>Category Distribution</h2>
            <ResponsiveContainer height={220}><BarChart data={cats}><CartesianGrid /><XAxis dataKey="category" /><YAxis /><Tooltip /><Bar dataKey="count" fill="#334155" /></BarChart></ResponsiveContainer>
          </div>
          <div>
            <h2>Agent Performance</h2>
            <ResponsiveContainer height={220}><PieChart><Pie data={cats} dataKey="count" nameKey="category">{cats.map((_, i) => <Cell key={i} fill={["#0f766e", "#b45309", "#be123c", "#475569"][i % 4]} />)}</Pie><Tooltip /></PieChart></ResponsiveContainer>
          </div>
        </div>
      </section>
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
