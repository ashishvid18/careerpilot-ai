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
  FileText,
  FolderOpen,
  Menu,
  Paperclip,
  Plus,
  Search,
  Settings2,
  Sparkles,
  UploadCloud,
  X,
} from "lucide-react";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

type Message = {
  role: "assistant" | "user";
  text: string;
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
  submission_reference?: string | null;
};

const SESSION_ID = "local-session";
const APPLICATION_STATUSES = [
  "saved_demo",
  "submitted",
  "under_review",
  "interview",
  "rejected",
  "offer",
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
      // Start a fresh conversation if saved data is invalid.
    }

    return [
      {
        role: "assistant",
        text: "Hi, I'm CareerPilot. I can help you make sense of your experience and find roles that fit. Upload your resume when you're ready, or tell me what kind of role you're looking for.",
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

  useEffect(() => {
    try {
      sessionStorage.setItem(
        "careerpilot.messages",
        JSON.stringify(messages)
      );

      sessionStorage.setItem(
        "careerpilot.profile",
        JSON.stringify(profile)
      );

      sessionStorage.setItem(
        "careerpilot.resumeName",
        resumeName
      );
    } catch (error) {
      console.error("Could not save CareerPilot session:", error);
    }
  }, [messages, profile, resumeName]);

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

  async function saveJob(job: Job) {
    setTrackerBusy(true);
    setError("");
    try {
      const res = await fetch(`${API}/api/applications`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: SESSION_ID, job_id: job.job_id }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Could not save this job.");
      setMessages((previous) => [
        ...previous,
        { role: "assistant", text: data.message || "Job saved to your tracker." },
      ]);
      await loadApplications();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save this job.");
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
      if (!res.ok) throw new Error(data.detail || "Could not update application status.");
      await loadApplications();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not update application status.");
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


  async function sendMessage(override?: string) {
  const message = (override ?? input).trim();

  if (!message || busy) return;

  setMessages((previous) => [
    ...previous,
    { role: "user", text: message },
  ]);

  setInput("");
  setBusy(true);
  setError("");

  try {
    const lower = message.toLowerCase();

    const asksForJobs =
      /\b(job|jobs|role|roles|position|positions|opportunit(?:y|ies))\b/.test(lower);

    const wantsMatching =
      /\b(match|matching|recommend|recommendation|find|show|search|only|filter|suitable|fit)\b/.test(lower);

    if (profile && asksForJobs && wantsMatching) {
      const remoteOnly =
        /\b(remote|work from home|work-from-home|wfh)\b/.test(lower);

      let keywords = "";

      const pythonOnly =
        /\bpython developer\b|\bonly python\b|\bpython jobs\b/.test(lower);
      const reactOnly =
        /\breact\b/.test(lower) && /\bonly\b|\bjobs?\b|\broles?\b/.test(lower);

      if (pythonOnly) {
        keywords = "Python";
      } else if (reactOnly) {
        keywords = "React";
      } else {
        const explicitMatch = lower.match(
          /(?:jobs?|roles?|positions?)\s+(?:for|requiring|needing|with)\s+([a-z0-9+#. -]+?)(?:\s+in\s+|\s+remote\b|$)/i
        );

        if (explicitMatch) {
          keywords = explicitMatch[1].trim();
        }
      }

      let location = "";
      const locationMatch = lower.match(
        /\bin\s+(bengaluru|bangalore|mumbai|pune|hyderabad|chennai|delhi|india)\b/i
      );

      if (locationMatch) {
        location =
          locationMatch[1].toLowerCase() === "bangalore"
            ? "Bengaluru"
            : locationMatch[1];
      }

      const params = new URLSearchParams({
        limit: "10",
        keywords,
        location,
        remote_only: String(remoteOnly),
      });

      const res = await fetch(`${API}/api/jobs/match?${params}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(profile),
      });

      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Job matching failed.");
      }

      const results: Job[] = Array.isArray(data.results) ? data.results : [];
      setMatchedJobs(results);

      const reply = results.length
        ? [
            "## Your matching jobs",
            `Found ${data.total} jobs matching your current filters. Here are the top ${results.length}:`,
            ...results.map((job: {
              title: string;
              company: string;
              location: string;
              match_score: number;
              match_reasons: string[];
              source_url: string;
              experience_required: string;
            }, index: number) =>
              [
                `### ${index + 1}. ${job.title}`,
                `**Company:** ${job.company}`,
                `**Location:** ${job.location}`,
                `**Match score:** ${job.match_score}/100`,
                `**Experience:** ${job.experience_required}`,
                `**Why it matches:** ${job.match_reasons.join("; ")}`,
                job.source_url
                  ? `[View original listing](${job.source_url})`
                  : "",
              ].filter(Boolean).join("\n\n")
            ),
          ].join("\n\n")
        : "I couldn't find jobs matching those filters in the current dataset. Try broadening your search.";

      setMessages((previous) => [
        ...previous,
        { role: "assistant", text: reply },
      ]);

      return;
    }

    const res = await fetch(`${API}/api/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        message,
        session_id: "local-session",
        resume_profile: profile,
      }),
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.detail || "Assistant could not respond.");
    }

    setMessages((previous) => [
      ...previous,
      { role: "assistant", text: data.reply },
    ]);
  } catch (e) {
    setError(
      e instanceof Error ? e.message : "Could not connect to backend."
    );
  } finally {
    setBusy(false);
  }
}


  async function upload(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];

    if (!file) return;

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

      setProfile(data.profile);

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          text: "I've extracted the profile details below. Please review them; resume extraction can miss or misread information.",
        },
      ]);
    } catch (e) {
      setError(
        e instanceof Error ? e.message : "Could not parse resume."
      );
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
        text: "New conversation started. Upload your resume or tell me about the roles you're targeting.",
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
            Your workspace <span>Local preview</span>
          </div>

          <button className="nav-item">
            <Settings2 size={17} /> Preferences
          </button>

          <div className="profile-mini">
            <div className="avatar">CP</div>
            <div className="profile-mini-copy">
              <strong>CareerPilot</strong>
              <span>Job search assistant</span>
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
            <strong>{trackerOpen ? "Application tracker" : "Find opportunities"}</strong>
          </div>

          <div className="topbar-right">
            <span className="status-indicator" />
            <span>Assistant ready</span>
            <button className="icon-button" aria-label="Settings">
              <Settings2 size={17} />
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
                    YOUR JOB SEARCH
                  </div>
                  <h1>Application tracker</h1>
                  <p className="intro-subtitle">
                    Keep track of saved jobs and update their progress.
                  </p>
                </div>
                <div className="tracker-toolbar">
                  <span>{applications.length} saved {applications.length === 1 ? "job" : "jobs"}</span>
                  <button className="text-action" onClick={() => void loadApplications()} disabled={trackerBusy}>
                    {trackerBusy ? "Refreshing..." : "Refresh tracker"} <span>↻</span>
                  </button>
                </div>
                {trackerBusy && <p className="tracker-empty">Loading applications...</p>}
                {!trackerBusy && applications.length === 0 && (
                  <div className="tracker-empty">
                    <FolderOpen size={28} />
                    <strong>No saved jobs yet</strong>
                    <p>Find matching jobs and select “Save job” to add them here.</p>
                    <button className="text-action" onClick={() => setTrackerOpen(false)}>
                      Find opportunities <span>→</span>
                    </button>
                  </div>
                )}
                <div className="application-list">
                  {applications.map((application) => {
                    const job = matchedJobs.find((item) => item.job_id === application.job_id);
                    return (
                      <article className="application-card" key={application.id}>
                        <div className="application-card-heading">
                          <div className="file-icon"><BriefcaseBusiness size={18} /></div>
                          <div className="application-card-title">
                            <strong>{job?.title || "Saved job"}</strong>
                            <span>{job?.company || `Job ID: ${application.job_id}`}</span>
                          </div>
                        </div>
                        {job && <p className="application-location">{job.location}</p>}
                        <div className="application-card-footer">
                          <label className="status-control">
                            <span>Status</span>
                            <select
                              value={application.status}
                              disabled={trackerBusy}
                              onChange={(event) => void updateApplicationStatus(application.job_id, event.target.value)}
                            >
                              {APPLICATION_STATUSES.map((status) => (
                                <option key={status} value={status}>{statusLabel(status)}</option>
                              ))}
                            </select>
                          </label>
                          <span className="application-date">
                            Saved {new Date(application.applied_at).toLocaleDateString()}
                          </span>
                        </div>
                        {job?.source_url && (
                          <a href={job.source_url} target="_blank" rel="noopener noreferrer">View original listing ↗</a>
                        )}
                      </article>
                    );
                  })}
                </div>
                {error && <div className="error-message"><span>{error}</span><button onClick={() => setError("")} aria-label="Dismiss error"><X size={14} /></button></div>}
              </section>
            ) : (
              <>
            <div className="intro-block">
              <div className="eyebrow">
                <span className="eyebrow-line" />
                YOUR NEXT CHAPTER
              </div>

              <h1>
                A better fit starts
                <br className="desktop-break" /> with a conversation.
              </h1>

              <p className="intro-subtitle">
                Share your experience. We'll work out what comes next.
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
                        CareerPilot <span>·</span> Assistant
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
                  </div>
                </div>
              ))}

              {matchedJobs.length > 0 && (
                <section className="matched-jobs-panel">
                  <div className="matched-jobs-heading">
                    <h2>Save a job for later</h2>
                    <span>{matchedJobs.length} matches</span>
                  </div>
                  {matchedJobs.map((job) => {
                    const alreadySaved = applications.some((application) => application.job_id === job.job_id);
                    return (
                      <article className="matched-job-card" key={job.job_id}>
                        <div className="matched-job-copy">
                          <strong>{job.title}</strong>
                          <span>{job.company} · {job.location}</span>
                          <small>Match score: {job.match_score}/100{job.experience_required ? ` · ${job.experience_required}` : ""}</small>
                        </div>
                        <button
                          className="text-action"
                          disabled={trackerBusy || alreadySaved}
                          onClick={() => void saveJob(job)}
                        >
                          {alreadySaved ? "Saved ✓" : "Save job +"}
                        </button>
                      </article>
                    );
                  })}
                  <button className="text-action" onClick={openTracker}>
                    Open application tracker <span>→</span>
                  </button>
                </section>
              )}

              {profile && (
                <section className="resume-summary">
                  <div className="resume-summary-head">
                    <div className="file-icon">
                      <FileText size={18} />
                    </div>

                    <div className="resume-file-copy">
                      <strong>{resumeName}</strong>
                      <span>Profile extracted · Review details</span>
                    </div>

                    <span className="review-tag">Review</span>
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
                      void sendMessage(
                        "Use my extracted resume profile to help me find matching jobs."
                      )
                    }
                    disabled={busy}
                  >
                    Find roles that fit <span>→</span>
                  </button>
                </section>
              )}

              {busy && (
                <div className="thinking">
                  <span />
                  <span />
                  <span />
                  <small>Working on it</small>
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
            </div>

            <div className="composer-area">
              <div className="suggestions">
                <button
                  onClick={() =>
                    void sendMessage(
                      "I'm looking for entry-level software engineering roles."
                    )
                  }
                >
                  Entry-level roles <span>↗</span>
                </button>

                <button
                  onClick={() =>
                    void sendMessage("Help me find remote jobs.")
                  }
                >
                  Remote work <span>↗</span>
                </button>

                <button onClick={() => fileRef.current?.click()}>
                  <UploadCloud size={14} /> Upload resume
                </button>
              </div>

              <form className="composer" onSubmit={submit}>
                <input
                  value={input}
                  onChange={(event) => setInput(event.target.value)}
                  placeholder="Tell me what kind of role you're looking for..."
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
                    <span>Attach resume</span>
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
                CareerPilot can make mistakes. Review extracted details before
                acting on them.
              </div>
            </div>
              </>
            )}
          </div>
        </section>

        <footer className="app-footer">
          <span>CAREERPILOT AI</span>
          <span>Thoughtful tools for your next move.</span>
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
      <span className="field-value">
        {value || <em>Not detected</em>}
      </span>
    </div>
  );
}
