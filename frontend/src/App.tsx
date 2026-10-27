import {
  ChangeEvent,
  FormEvent,
  useEffect,
  useRef,
  useState,
} from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import {
  ArrowUp,
  BriefcaseBusiness,
  CheckCircle2,
  ExternalLink,
  FileText,
  FolderOpen,
  Menu,
  Paperclip,
  Plus,
  RefreshCw,
  Search,
  Settings2,
  Sparkles,
  UploadCloud,
  X,
} from "lucide-react";

// Automatically detect backend API: relative in production/FastAPI or localhost:8000 in dev
const API =
  import.meta.env.VITE_API_URL ||
  (typeof window !== "undefined" && window.location.port === "5173"
    ? "http://127.0.0.1:8000"
    : "");

type Message = {
  role: "assistant" | "user";
  text: string;
  suggestedActions?: string[];
};

type Profile = {
  name?: string | null;
  email?: string | null;
  phone?: string | null;
  designation?: string | null;
  skills?: string[];
  experience?: string | null;
  education?: string[];
  projects?: string[];
};

type Job = {
  job_id: string;
  title: string;
  company: string;
  location: string;
  experience_required: string;
  skills: string[];
  description: string;
  source: string;
  source_url: string;
  match_score: number;
  match_reasons: string[];
};

type Application = {
  id: number;
  session_id: string;
  job_id: string;
  applied_at: string;
  status: string;
  title?: string;
  company?: string;
  location?: string;
  source_url?: string;
};

const SESSION_ID = "local-session";
const APPLICATION_STATUSES = [
  "submitted",
  "under_review",
  "interview",
  "offer",
  "rejected",
  "saved_demo",
  "withdrawn",
];

export default function App() {
  const [messages, setMessages] = useState<Message[]>(() => {
    try {
      const saved = sessionStorage.getItem("careerpilot.messages");
      if (saved) {
        const parsed: unknown = JSON.parse(saved);
        if (
          Array.isArray(parsed) &&
          parsed.every(
            (item) =>
              item &&
              (item.role === "assistant" || item.role === "user") &&
              typeof item.text === "string"
          )
        ) {
          return parsed as Message[];
        }
      }
    } catch {
      // fallback
    }

    return [
      {
        role: "assistant",
        text: "Hi, I'm **CareerPilot**, your AI Job Search Assistant! 🚀\n\nI can analyze your resume, recommend matched opportunities from our database of **1,800+ real job listings**, refine results naturally, and apply on your behalf.\n\nTo begin, **upload your resume** (PDF or DOCX) using the clip below, or simply ask for roles you're interested in!",
        suggestedActions: [
          "Upload resume",
          "Find Python Developer jobs",
          "Show remote roles",
          "Show my applied jobs",
        ],
      },
    ];
  });

  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);

  const [profile, setProfile] = useState<Profile | null>(() => {
    try {
      const saved = sessionStorage.getItem("careerpilot.profile");
      return saved ? (JSON.parse(saved) as Profile) : null;
    } catch {
      return null;
    }
  });

  const [resumeName, setResumeName] = useState(
    () => sessionStorage.getItem("careerpilot.resumeName") || ""
  );

  const [error, setError] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [matchedJobs, setMatchedJobs] = useState<Job[]>([]);
  const [applications, setApplications] = useState<Application[]>([]);
  const [trackerOpen, setTrackerOpen] = useState(false);
  const [trackerBusy, setTrackerBusy] = useState(false);

  const fileRef = useRef<HTMLInputElement>(null);
  const threadEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    try {
      sessionStorage.setItem("careerpilot.messages", JSON.stringify(messages));
      sessionStorage.setItem("careerpilot.profile", JSON.stringify(profile));
      sessionStorage.setItem("careerpilot.resumeName", resumeName);
    } catch (error) {
      console.error("Could not save session:", error);
    }
  }, [messages, profile, resumeName]);

  useEffect(() => {
    threadEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, busy]);

  async function loadApplications() {
    setTrackerBusy(true);
    setError("");
    try {
      const params = new URLSearchParams({ session_id: SESSION_ID });
      const res = await fetch(`${API}/api/applications?${params}`);
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Could not load applications.");
      setApplications(Array.isArray(data.applications) ? data.applications : []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not load applications.");
    } finally {
      setTrackerBusy(false);
    }
  }

  async function updateApplicationStatus(jobId: string, status: string) {
    setTrackerBusy(true);
    setError("");
    try {
      const res = await fetch(`${API}/api/applications/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: SESSION_ID, job_id: jobId, status }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Could not update status.");
      await loadApplications();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not update status.");
    } finally {
      setTrackerBusy(false);
    }
  }

  function openTracker() {
    setTrackerOpen(true);
    setSidebarOpen(false);
    void loadApplications();
  }

  function statusLabel(status: string): string {
    return status
      .replace(/_/g, " ")
      .replace(/\b\w/g, (letter: string) => letter.toUpperCase());
  }

  async function sendMessage(override?: string, explicitProfile?: Profile | null) {
    const message = (override ?? input).trim();
    if (!message || busy) return;

    if (override === "Upload resume") {
      fileRef.current?.click();
      return;
    }

    setMessages((previous) => [
      ...previous,
      { role: "user", text: message },
    ]);

    setInput("");
    setBusy(true);
    setError("");

    const targetProfile = explicitProfile !== undefined ? explicitProfile : profile;

    try {
      const res = await fetch(`${API}/api/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message,
          session_id: SESSION_ID,
          resume_profile: targetProfile,
          current_jobs: matchedJobs,
        }),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Assistant could not respond.");
      }

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          text: data.reply,
          suggestedActions: data.suggested_actions,
        },
      ]);

      if (Array.isArray(data.jobs) && data.jobs.length > 0) {
        setMatchedJobs(data.jobs);
      }

      if (Array.isArray(data.applications)) {
        setApplications(data.applications);
      }
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Could not connect to backend assistant."
      );
    } finally {
      setBusy(false);
    }
  }

  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;

    const suffix = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();
    if (![".pdf", ".docx"].includes(suffix)) {
      setError("Please upload a PDF or DOCX resume.");
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      setError("File exceeds 10MB limit.");
      return;
    }

    setResumeName(file.name);
    setMessages((previous) => [
      ...previous,
      { role: "user", text: `Uploaded resume: ${file.name}` },
    ]);

    setBusy(true);
    setError("");

    const body = new FormData();
    body.append("file", file);

    try {
      const res = await fetch(`${API}/api/resume/parse`, {
        method: "POST",
        body,
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Resume parsing failed.");
      }

      const parsedProfile: Profile = data.profile;
      setProfile(parsedProfile);

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          text: `✅ **Resume successfully parsed!**\n\nI have extracted your candidate details below (Name, Designation, Skills, Experience, Education, and Projects). Review them, and let's find the best matching roles from our 1,800+ job database!`,
          suggestedActions: [
            "Recommend matching jobs",
            "Show only remote roles",
            "Jobs needing React",
          ],
        },
      ]);

      // Automatically trigger recommendation for the newly uploaded resume profile
      await sendMessage("Find matching jobs for my profile", parsedProfile);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not parse resume.");
    } finally {
      setBusy(false);
      if (fileRef.current) {
        fileRef.current.value = "";
      }
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void sendMessage();
  }

  function newChat() {
    setMessages([
      {
        role: "assistant",
        text: "New conversation started! Upload your resume (PDF or DOCX) or tell me about the roles you are targeting.",
        suggestedActions: [
          "Upload resume",
          "Find Python Developer jobs",
          "Show remote roles",
          "Show my applied jobs",
        ],
      },
    ]);
    setProfile(null);
    setResumeName("");
    setMatchedJobs([]);
    setTrackerOpen(false);
    setError("");
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${sidebarOpen ? "sidebar-open" : ""}`}>
        <div className="brand-row">
          <div className="brand-mark">
            <BriefcaseBusiness size={18} />
          </div>
          <span className="brand-name">
            careerpilot<span className="brand-period">.</span>
          </span>
          <button
            className="icon-button mobile-close"
            onClick={() => setSidebarOpen(false)}
            aria-label="Close menu"
          >
            <X size={18} />
          </button>
        </div>

        <button className="new-chat" onClick={newChat}>
          <Plus size={17} /> New conversation
          <span className="shortcut">⌘ K</span>
        </button>

        <div className="side-label">WORKSPACE</div>

        <button
          className={`nav-item ${!trackerOpen ? "active" : ""}`}
          onClick={() => {
            setTrackerOpen(false);
            setSidebarOpen(false);
          }}
        >
          <Search size={17} /> Find opportunities
        </button>

        <button
          className={`nav-item ${trackerOpen ? "active" : ""}`}
          onClick={openTracker}
        >
          <FolderOpen size={17} /> Application tracker
        </button>

        <div className="side-bottom">
          <div className="privacy-note">
            <span className="privacy-dot" />
            Your workspace <span>1,800+ Jobs</span>
          </div>

          <button className="nav-item" onClick={() => void sendMessage("Help")}>
            <Settings2 size={17} /> Assistant Guide
          </button>

          <div className="profile-mini">
            <div className="avatar">CP</div>
            <div className="profile-mini-copy">
              <strong>CareerPilot AI</strong>
              <span>Orchestrator Agent</span>
            </div>
          </div>
        </div>
      </aside>

      {sidebarOpen && (
        <button
          className="scrim"
          aria-label="Close navigation"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      <main className="main-panel">
        <header className="topbar">
          <div className="topbar-left">
            <button
              className="icon-button mobile-menu"
              onClick={() => setSidebarOpen(true)}
              aria-label="Open menu"
            >
              <Menu size={19} />
            </button>
            <span className="breadcrumb-muted">Workspace</span>
            <span className="crumb-slash">/</span>
            <strong>
              {trackerOpen ? "Application tracker" : "AI Job Chat Assistant"}
            </strong>
          </div>

          <div className="topbar-right">
            <span className="status-indicator" />
            <span>Agent Orchestrator Ready</span>
            <button
              className="icon-button"
              onClick={openTracker}
              title="Open Application Tracker"
              aria-label="Tracker"
            >
              <FolderOpen size={17} />
            </button>
          </div>
        </header>

        <section className="conversation">
          <div className="conversation-inner">
            {trackerOpen ? (
              <section className="tracker-view">
                <div className="intro-block">
                  <div className="eyebrow">
                    <span className="eyebrow-line" />
                    JOB APPLICATION TRACKER
                  </div>
                  <h1>Track your applications</h1>
                  <p className="intro-subtitle">
                    Recorded applications with timestamps and status updates. Duplicates are strictly prevented.
                  </p>
                </div>
                <div className="tracker-toolbar">
                  <span>
                    {applications.length} recorded{" "}
                    {applications.length === 1 ? "application" : "applications"}
                  </span>
                  <button
                    className="text-action"
                    style={{ width: "auto", border: "none" }}
                    onClick={() => void loadApplications()}
                    disabled={trackerBusy}
                  >
                    <RefreshCw size={14} /> Refresh tracker
                  </button>
                </div>
                {trackerBusy && <p className="tracker-empty">Loading records...</p>}
                {!trackerBusy && applications.length === 0 && (
                  <div className="tracker-empty">
                    <FolderOpen size={28} />
                    <strong>No applications recorded yet</strong>
                    <p>
                      Chat with CareerPilot to discover matching jobs and say{" "}
                      <em>"Apply to job 1"</em> to submit applications!
                    </p>
                    <button
                      className="text-action"
                      style={{ width: "auto" }}
                      onClick={() => setTrackerOpen(false)}
                    >
                      Back to Chat <span>→</span>
                    </button>
                  </div>
                )}
                <div className="application-list">
                  {applications.map((app) => (
                    <article className="application-card" key={app.id || app.job_id}>
                      <div className="application-card-heading">
                        <div className="file-icon">
                          <BriefcaseBusiness size={18} />
                        </div>
                        <div className="application-card-title">
                          <strong>{app.title || "Applied Job"}</strong>
                          <span>
                            {app.company || `Job ID: ${app.job_id}`}
                          </span>
                        </div>
                      </div>
                      {app.location && (
                        <p className="application-location">{app.location}</p>
                      )}
                      <div className="application-card-footer">
                        <label className="status-control">
                          <span>Status:</span>
                          <select
                            value={app.status}
                            disabled={trackerBusy}
                            onChange={(e) =>
                              void updateApplicationStatus(app.job_id, e.target.value)
                            }
                          >
                            {APPLICATION_STATUSES.map((status) => (
                              <option key={status} value={status}>
                                {statusLabel(status)}
                              </option>
                            ))}
                          </select>
                        </label>
                        <span className="application-date">
                          Applied: {app.applied_at || "Recent"}
                        </span>
                      </div>
                      {app.source_url && (
                        <a
                          href={app.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          style={{
                            fontSize: "11px",
                            color: "#315d46",
                            display: "inline-flex",
                            alignItems: "center",
                            gap: "4px",
                          }}
                        >
                          View Original Listing <ExternalLink size={12} />
                        </a>
                      )}
                    </article>
                  ))}
                </div>
                {error && (
                  <div className="error-message">
                    <span>{error}</span>
                    <button onClick={() => setError("")} aria-label="Dismiss">
                      <X size={14} />
                    </button>
                  </div>
                )}
              </section>
            ) : (
              <>
                <div className="intro-block">
                  <div className="eyebrow">
                    <span className="eyebrow-line" />
                    AI JOB CHAT ASSISTANT
                  </div>
                  <h1>
                    Your career, matched.
                    <br className="desktop-break" /> Powered by AI Agents.
                  </h1>
                  <p className="intro-subtitle">
                    Upload your resume to parse your skills, explore 1,800+ real job listings, refine your search naturally, and apply instantly.
                  </p>
                </div>

                <div className="thread">
                  {messages.map((message, index) => (
                    <div
                      className={`message-row ${message.role}`}
                      key={`${index}-${message.role}`}
                    >
                      {message.role === "assistant" && (
                        <div className="assistant-avatar">
                          <Sparkles size={15} />
                        </div>
                      )}

                      <div className={`message-content ${message.role}`}>
                        {message.role === "assistant" && (
                          <div className="message-author">
                            CareerPilot <span>·</span> Orchestrator Agent
                          </div>
                        )}

                        <div className="markdown-content">
                          <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                              a: ({ href, children, ...props }) => (
                                <a
                                  href={href}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  {...props}
                                >
                                  {children}
                                </a>
                              ),
                            }}
                          >
                            {message.text}
                          </ReactMarkdown>
                        </div>

                        {/* Interactive Suggestion Pills */}
                        {message.suggestedActions && message.suggestedActions.length > 0 && (
                          <div className="action-chips">
                            {message.suggestedActions.map((action) => (
                              <button
                                key={action}
                                className="action-chip"
                                onClick={() => void sendMessage(action)}
                                disabled={busy}
                              >
                                {action} <span>↗</span>
                              </button>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}

                  {/* Extracted Resume Profile Review Card */}
                  {profile && (
                    <section className="resume-summary">
                      <div className="resume-summary-head">
                        <div className="file-icon">
                          <FileText size={18} />
                        </div>
                        <div className="resume-file-copy">
                          <strong>{resumeName || "Uploaded Resume"}</strong>
                          <span>Auto-parsed Candidate Profile · All 7 Fields Extracted</span>
                        </div>
                        <span className="review-tag">Parsed</span>
                      </div>

                      <div className="profile-grid">
                        <Field label="NAME" value={profile.name} />
                        <Field label="DESIGNATION" value={profile.designation} />
                        <Field label="EMAIL" value={profile.email} />
                        <Field label="PHONE" value={profile.phone} />

                        <div className="profile-field full">
                          <span className="field-label">SKILLS</span>
                          <div className="skill-list">
                            {(profile.skills || []).length ? (
                              profile.skills!.map((skill) => (
                                <span className="skill-chip" key={skill}>
                                  {skill}
                                </span>
                              ))
                            ) : (
                              <em>Not detected</em>
                            )}
                          </div>
                        </div>

                        <Field
                          label="EXPERIENCE"
                          value={profile.experience}
                        />

                        <Field
                          label="EDUCATION"
                          value={(profile.education || []).join(" · ")}
                        />

                        <div className="profile-field full">
                          <span className="field-label">PROJECTS</span>
                          <span className="field-value">
                            {(profile.projects || []).join(" · ") || (
                              <em>Not detected</em>
                            )}
                          </span>
                        </div>
                      </div>

                      <button
                        className="text-action"
                        onClick={() =>
                          void sendMessage("Find matching jobs for my profile")
                        }
                        disabled={busy}
                      >
                        Re-match opportunities for this profile <span>→</span>
                      </button>
                    </section>
                  )}

                  {/* Matched Jobs Card Actions */}
                  {matchedJobs.length > 0 && (
                    <section className="matched-jobs-panel">
                      <div className="matched-jobs-heading">
                        <h2>Quick Apply / Save Jobs</h2>
                        <span>{matchedJobs.length} active matches</span>
                      </div>
                      {matchedJobs.map((job, idx) => {
                        const alreadyApplied = applications.some(
                          (app) => app.job_id === job.job_id
                        );
                        return (
                          <article className="matched-job-card" key={job.job_id}>
                            <div className="matched-job-copy">
                              <strong>
                                #{idx + 1}. {job.title}
                              </strong>
                              <span>
                                {job.company} · {job.location}
                              </span>
                              <small>
                                Match score: {job.match_score}/100
                                {job.experience_required
                                  ? ` · ${job.experience_required}`
                                  : ""}
                              </small>
                            </div>
                            <button
                              className="action-chip"
                              disabled={busy || alreadyApplied}
                              onClick={() => void sendMessage(`Apply to job ${idx + 1}`)}
                            >
                              {alreadyApplied ? (
                                <>
                                  <CheckCircle2 size={13} /> Applied
                                </>
                              ) : (
                                <>Apply now →</>
                              )}
                            </button>
                          </article>
                        );
                      })}
                      <button
                        className="text-action"
                        onClick={openTracker}
                        style={{ marginTop: "10px" }}
                      >
                        Open Application Tracker <span>→</span>
                      </button>
                    </section>
                  )}

                  {busy && (
                    <div className="thinking">
                      <span />
                      <span />
                      <span />
                      <small>Orchestrator Agent reasoning...</small>
                    </div>
                  )}

                  {error && (
                    <div className="error-message">
                      <span>{error}</span>
                      <button
                        onClick={() => setError("")}
                        aria-label="Dismiss error"
                      >
                        <X size={14} />
                      </button>
                    </div>
                  )}

                  <div ref={threadEndRef} />
                </div>

                <div className="composer-area">
                  <div className="suggestions">
                    <button
                      onClick={() =>
                        void sendMessage("Find matching jobs for my profile")
                      }
                    >
                      Recommend matching jobs <span>↗</span>
                    </button>
                    <button
                      onClick={() => void sendMessage("Show only remote roles")}
                    >
                      Remote roles <span>↗</span>
                    </button>
                    <button
                      onClick={() => void sendMessage("Show jobs needing React")}
                    >
                      Jobs with React <span>↗</span>
                    </button>
                    <button
                      onClick={() => void sendMessage("Show my applied jobs")}
                    >
                      Applied jobs <span>↗</span>
                    </button>
                    <button onClick={() => fileRef.current?.click()}>
                      <UploadCloud size={14} /> Upload resume
                    </button>
                  </div>

                  <form className="composer" onSubmit={submit}>
                    <input
                      value={input}
                      onChange={(event) => setInput(event.target.value)}
                      placeholder="Ask CareerPilot (e.g. 'Apply to job 1', 'Show remote roles')..."
                      aria-label="Message CareerPilot"
                      disabled={busy}
                    />

                    <div className="composer-tools">
                      <button
                        type="button"
                        className="attach-button"
                        onClick={() => fileRef.current?.click()}
                      >
                        <Paperclip size={17} />
                        <span>Attach resume (PDF/DOCX)</span>
                      </button>

                      <div className="composer-right">
                        <span className="enter-hint">Enter to send</span>
                        <button
                          type="submit"
                          className="send-button"
                          disabled={!input.trim() || busy}
                          aria-label="Send message"
                        >
                          <ArrowUp size={18} />
                        </button>
                      </div>
                    </div>
                  </form>

                  <input
                    ref={fileRef}
                    type="file"
                    accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    hidden
                    onChange={upload}
                  />

                  <div className="disclaimer">
                    CareerPilot AI Orchestrator: Multi-Agent Architecture for Resume Parsing, Job Matching & Application Tracking.
                  </div>
                </div>
              </>
            )}
          </div>
        </section>

        <footer className="app-footer">
          <span>CAREERPILOT AI · HIDANI TECH ASSESSMENT</span>
          <span>1,800+ Live Jobs · Agent Orchestration · Full Functional Flow</span>
        </footer>
      </main>
    </div>
  );
}

function Field({
  label,
  value,
}: {
  label: string;
  value?: string | null;
}) {
  return (
    <div className="profile-field">
      <span className="field-label">{label}</span>
      <span className="field-value">{value || <em>Not detected</em>}</span>
    </div>
  );
}

