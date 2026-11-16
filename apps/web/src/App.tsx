import { useEffect, useRef, useState, type FormEvent } from "react";
import { request, type Asset, type DashboardSummary, type Job, type JobKind } from "./api";
import { Icon, type IconName } from "./Icon";
import { AuditPanel, InboxPanel, IntakePanel, StockPanel } from "./OperationsPanels";
import { roleLabels, type Audit, type Inbox, type Intake, type Movement, type Role, type Stock, type User } from "./operations";
import { AssetView, ChangeView, Dashboard, EmptyTable, Heading, IssueView, LocationView } from "./WorkspaceViews";

const roleOptions = Object.entries(roleLabels) as [Role, string][];
const navigation = {
  home: { label: "대시보드", icon: "home" },
  assets: { label: "자산 현황", icon: "box", children: { all: "전체 자산", issues: "불일치 자산" } },
  audits: { label: "실사 관리", icon: "audit", children: { all: "실사 진행 현황", issues: "불일치 확인" } },
  reports: { label: "보고서", icon: "report", children: { all: "자산 현황 보고서", audit: "실사 보고서" } },
  changes: { label: "변동 사항", icon: "swap" },
  locations: { label: "위치 조회", icon: "pin" },
  intake: { label: "납품·입고", icon: "truck" },
  stock: { label: "수량 재고", icon: "box" },
  notices: { label: "공지사항", icon: "meg" },
  inbox: { label: "알림함", icon: "bell" },
} satisfies Record<string, { label: string; icon: IconName; children?: Record<string, string> }>;
type Page = keyof typeof navigation;
type Workspace = {
  summary: DashboardSummary | null; assets: Asset[]; intakes: Intake[]; audits: Audit[];
  stock: Stock[]; changes: Movement[]; inbox: Inbox;
};
const empty: Workspace = {
  summary: null, assets: [], intakes: [], audits: [], stock: [], changes: [], inbox: { unread: 0, items: [] },
};

async function readWorkspace(token: string, user: User): Promise<Workspace> {
  const manage = user.role === "asset_manager" || user.role === "purchasing";
  const internal = user.role !== "vendor";
  const [summary, assets, intakes, audits, stock, changes, inbox] = await Promise.all([
    internal ? request<DashboardSummary>("/dashboard", token) : null,
    internal ? request<Asset[]>("/assets", token) : [],
    user.role === "employee" ? [] : request<Intake[]>("/intakes", token),
    manage ? request<Audit[]>("/audits", token) : [],
    manage ? request<Stock[]>("/stock", token) : [],
    manage ? request<Movement[]>("/movements", token) : [],
    request<Inbox>("/notifications", token),
  ]);
  return { summary, assets, intakes, audits, stock, changes, inbox };
}

export function App() {
  const [token, setToken] = useState("");
  const [user, setUser] = useState<User | null>(null);
  const [role, setRole] = useState<Role>("asset_manager");
  const [data, setData] = useState<Workspace>(empty);
  const [page, setPage] = useState<Page>("home");
  const [section, setSection] = useState("all");
  const [menu, setMenu] = useState(false);
  const [chat, setChat] = useState(false);
  const [search, setSearch] = useState("");
  const searchDialog = useRef<HTMLDialogElement>(null);
  const [assetSearch, setAssetSearch] = useState({ value: "", version: 0 });
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const jobId = job?.id;
  const internal = user !== null && user.role !== "vendor";
  const manage = user?.role === "asset_manager" || user?.role === "purchasing";

  useEffect(() => {
    if (!internal) return;
    function openSearch(event: KeyboardEvent) {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        if (!searchDialog.current?.open) searchDialog.current?.showModal();
      }
    }
    window.addEventListener("keydown", openSearch);
    return () => window.removeEventListener("keydown", openSearch);
  }, [internal]);

  useEffect(() => {
    if (!jobId || !token) return;
    let active = true;
    let timer: ReturnType<typeof setTimeout> | undefined;
    async function poll() {
      try {
        const next = await request<Job>(`/jobs/${jobId}`, token);
        if (!active) return;
        setJob(next);
        if (next.status === "queued" || next.status === "running") timer = setTimeout(poll, 1000);
      } catch (reason) {
        if (active) setError(String(reason));
      }
    }
    void poll();
    return () => { active = false; clearTimeout(timer); };
  }, [jobId, token]);

  async function login(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const { access_token } = await request<{ access_token: string }>("/auth/dev-token", undefined, { role });
      const current = await request<User>("/auth/me", access_token);
      setData(await readWorkspace(access_token, current));
      setToken(access_token);
      setUser(current);
      navigate(current.role === "vendor" ? "intake" : "home");
    } catch (reason) { setError(String(reason)); }
    finally { setBusy(false); }
  }

  function logout() {
    setToken("");
    setUser(null);
    setData(empty);
    setJob(null);
    setChat(false);
    setSearch("");
    setError("");
  }

  async function action(work: () => Promise<unknown>) {
    if (busy || !user) return;
    setBusy(true);
    setError("");
    try {
      await work();
      setData(await readWorkspace(token, user));
    } catch (reason) { setError(String(reason)); }
    finally { setBusy(false); }
  }

  function navigate(next: Page, subsection = "all", query = "") {
    setPage(next);
    setSection(subsection);
    setMenu(false);
    if (next === "assets") setAssetSearch(({ version }) => ({ value: query, version: version + 1 }));
    window.scrollTo(0, 0);
  }

  function submitJob(kind: Extract<JobKind, "inspection" | "monitoring">, fields: Record<string, unknown> = {}) {
    void action(async () => setJob(await request<Job>("/jobs", token, { kind, ...fields })));
  }

  if (!user) return <main className="login-screen">
    <section className="login-panel">
      <div className="login-brand"><Brand /></div>
      <div><h1>자산관리 업무 공간</h1><p className="muted">개발용 계정으로 업무 화면을 열 수 있습니다.</p></div>
      <form className="stack" onSubmit={login}>
        <label>개발용 계정<select value={role} onChange={(event) => setRole(event.target.value as Role)}>
          {roleOptions.map(([key, label]) => <option key={key} value={key}>{label}</option>)}
        </select></label>
        <button disabled={busy}>{busy ? "불러오는 중…" : "대시보드 열기"}</button>
      </form>
      {error && <p className="error" role="alert">{error}</p>}
    </section>
  </main>;

  const workPages: Page[] = !internal ? ["intake"] : manage
    ? ["home", "assets", "audits", "reports", "changes", "locations", "intake", "stock"] : ["home", "assets", "locations"];
  const activeNavigation = navigation[page];
  const auditReport = section === "audit";
  const department = user.role === "purchasing" ? "전체 부서" : user.department;
  const reportTitle = auditReport ? "실사 보고서" : "자산 현황 보고서";

  function navItem(key: Page) {
    const item = navigation[key];
    const selected = page === key;
    const children = "children" in item ? Object.entries(item.children).filter(([id]) => manage || id !== "issues") : [];
    const expandable = children.length > 1;
    return <div key={key}>
      <button className={`nav-btn ${selected ? "active" : ""}`} aria-current={selected && !expandable ? "page" : undefined}
        aria-expanded={expandable ? selected : undefined} onClick={() => navigate(key)}>
        <Icon name={item.icon} />{item.label}{expandable && <Icon className="chev" name={selected ? "down" : "arrow"} />}
      </button>
      {selected && expandable && <div className="nav-children">{children.map(([id, label]) =>
        <button key={id} aria-current={id === section ? "page" : undefined} onClick={() => navigate(key, id)}>{label}</button>)}</div>}
    </div>;
  }

  return <div className="app-shell">
    {menu && <button type="button" className="menu-scrim" aria-label="메뉴 닫기" onClick={() => setMenu(false)} />}
    <aside className={`sidebar ${menu ? "open" : ""}`} aria-label="주 메뉴">
      <button className="brand-button" aria-label="WonQ 홈" onClick={() => navigate(workPages[0])}><Brand /></button>
      <nav aria-label="업무 공간"><div className="nav-label">업무 공간</div>{workPages.map(navItem)}</nav>
      <div className="sidebar-bottom">
        <div className="nav-label">소식</div>{internal && navItem("notices")}{navItem("inbox")}
        <div className="side-foot"><i />사내 자산관리</div>
      </div>
    </aside>
    <div className="shell-content">
      <header className="topbar">
        <button className="icon-button mobile-menu" aria-label="메뉴 열기" aria-expanded={menu} onClick={() => setMenu(!menu)}><Icon name="menu" /></button>
        <div className="crumb"><span>업무 공간</span><Icon name="arrow" /><b>{activeNavigation.label}</b></div>
        <div className="top-actions">
          {internal && <button className="top-search" aria-label="통합 검색" onClick={() => searchDialog.current?.showModal()}>
            <Icon name="search" /><span>자산·담당자 검색</span><kbd>Ctrl K</kbd>
          </button>}
          <button className="icon-button" aria-label={data.inbox.unread ? `알림함, 읽지 않은 알림 ${data.inbox.unread}개` : "알림함"}
            onClick={() => navigate("inbox")}><Icon name="bell" />
            {data.inbox.unread > 0 && <span className="bell-badge" aria-hidden="true">{data.inbox.unread}</span>}</button>
          <details className="profile-menu">
            <summary className="profile" aria-label="계정 메뉴">
              <span className="avatar"><Icon name="user" /></span><span className="profile-text"><b>{roleLabels[user.role]}</b><small>개발용 계정</small></span>
              <Icon className="chev" name="down" />
            </summary>
            <div className="profile-options">
              <button className="secondary" disabled={busy} onClick={() => void action(async () => undefined)}><Icon name="refresh" />새로고침</button>
              <button className="secondary" disabled={busy} onClick={logout}>로그아웃</button>
            </div>
          </details>
        </div>
      </header>
      <main className="workspace" aria-busy={busy}>
        {error && <p className="error" role="alert">{error}</p>}
        {page === "home" && data.summary && <Dashboard summary={data.summary} changes={data.changes} department={department} manage={manage}
          browse={() => navigate("assets")} audit={() => navigate("audits")} issues={() => navigate("audits", "issues")}
          history={() => navigate("changes")} intake={() => navigate("intake")} notices={() => navigate("notices")} />}
        {page === "assets" && (section === "issues" ? <>
          <Heading title="불일치 자산" description="실사에서 확인한 미발견·불일치 기록입니다." />
          <IssueView audits={data.audits} />
        </> : <>
          <Heading title="자산 현황" description="자산을 조회하고 QR로 상세 정보를 확인하세요.">
            {manage && <button className="action-button" onClick={() => navigate("intake")}><Icon name="plus" />자산 등록</button>}
          </Heading>
          <AssetView key={assetSearch.version} token={token} rows={data.assets} search={assetSearch.value} />
        </>)}
        {page === "audits" && <>
          <Heading title={section === "issues" ? "불일치 확인" : "실사 관리"} description="실사 대상 자산을 확인하고 결과를 기록하세요.">
            <button className="secondary action-button" onClick={() => navigate("reports", "audit")}><Icon name="report" />실사 보고서</button>
          </Heading>
          {section === "issues" ? <IssueView audits={data.audits} /> : <AuditPanel items={data.audits} user={user} token={token} action={action} analyze={(id) => {
            navigate("reports", "audit"); submitJob("inspection", { audit_id: id });
          }} />}
        </>}
        {page === "intake" && <><Heading title="납품·입고" description="납품 요청, 검수 및 입고 상태를 확인하세요." />
          <IntakePanel items={data.intakes} user={user} token={token} action={action} /></>}
        {page === "stock" && <><Heading title="수량 재고" description="품목별 현재고와 안전재고 기준을 관리하세요.">
          <button className="secondary action-button" disabled={busy} onClick={() => submitJob("monitoring")}>안전재고 점검</button>
        </Heading><div className="stack"><StockPanel rows={data.stock} token={token} action={action} />
          {job?.kind === "monitoring" && <JobResult job={job} />}</div></>}
        {page === "changes" && <><Heading title="변동 사항" description="확정된 입고와 수량 재고의 수불 기록을 확인하세요." />
          <ChangeView rows={data.changes} /></>}
        {page === "locations" && <><Heading title="위치 조회" description="층별 도면에서 구역을 선택해 보관 자산을 조회하는 화면입니다." /><LocationView /></>}
        {page === "notices" && <><Heading title="공지사항" description="자산 관리 공지와 긴급 안내를 확인하는 화면입니다.">
          {manage && <button className="action-button" disabled><Icon name="plus" />공지 작성</button>}
        </Heading><EmptyTable title="공지 목록" headers={["구분", "제목", "게시일"]} message="표시할 공지가 없습니다." /></>}
        {page === "inbox" && <><Heading title="알림함" description="업무에 대한 알림을 확인하세요." />
          <InboxPanel inbox={data.inbox} token={token} action={action} /></>}
        {page === "reports" && <><Heading title={reportTitle}>
          <button className="action-button" disabled><Icon name="download" />보고서 내려받기</button>
        </Heading><div className="stack">
          {auditReport
            ? <EmptyTable title="부서별 실사 집계" headers={["부서", "실사 대상", "일치", "불일치", "미확인"]} message="생성된 보고서가 없습니다." />
            : <EmptyTable title="분류별 자산 집계" headers={["분류", "등록 자산", "보관", "사용 중", "폐기"]} message="생성된 보고서가 없습니다." />}
          {auditReport && job?.kind === "inspection" && <JobResult job={job} />}
        </div></>}
      </main>
    </div>
    {internal && <>
      <dialog className="dialog" ref={searchDialog} aria-labelledby="search-title">
        <div className="dialog-head"><h2 id="search-title">통합 검색</h2>
          <button className="icon-button" aria-label="검색 닫기" onClick={() => searchDialog.current?.close()}><Icon name="close" /></button></div>
        <form className="dialog-body stack" onSubmit={(event) => {
          event.preventDefault(); searchDialog.current?.close(); navigate("assets", "all", search.trim()); setSearch("");
        }}>
          <div className="tabs"><span className="tab active">자산</span><button className="tab" type="button" disabled>담당자</button></div>
          <label>검색어<input autoFocus type="search" placeholder="자산명 또는 코드 검색" value={search} maxLength={128}
            onChange={(event) => setSearch(event.target.value)} /></label><button type="submit">자산 검색</button>
        </form>
      </dialog>
      {chat && <section id="chat-panel" aria-label="WonQ 도우미" className="chat-panel">
        <div className="chat-head"><span><Icon name="chat" />WonQ 도우미</span>
          <button className="icon-button" aria-label="도우미 닫기" onClick={() => setChat(false)}><Icon name="close" /></button></div>
        <div className="chat-messages" role="log" aria-label="대화 내역" />
        <div className="chat-form"><input aria-label="도우미에게 질문" placeholder="자산에 대해 질문하기" disabled />
          <button className="icon-button" aria-label="질문 보내기" disabled><Icon name="send" /></button></div>
        <p className="chat-status">챗봇 연결 준비 중</p>
      </section>}
      <button className="chat-launch" aria-controls="chat-panel" aria-expanded={chat} onClick={() => setChat(!chat)}>
        <Icon name="chat" />WonQ 도우미</button>
    </>}
  </div>;
}

function Brand() {
  return <span className="brand"><span className="brand-mark" aria-hidden="true"><i>W</i></span>
    <span><strong>WonQ</strong><small>사내 자산관리</small></span></span>;
}

function JobResult({ job }: { job: Job }) {
  const status = { queued: "대기 중", running: "처리 중", completed: "완료", failed: "실패" };
  return <section className="panel" aria-live="polite"><h2>{job.kind === "inspection" ? "실사 분석" : "안전재고 점검"} · {status[job.status]}</h2>
    {job.result && <pre>{JSON.stringify(job.result, null, 2)}</pre>}</section>;
}
