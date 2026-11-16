import { lazy, Suspense, useCallback, useEffect, useState, type ReactNode } from "react";
import { request, type Asset, type DashboardSummary } from "./api";
import { Icon, type IconName } from "./Icon";
import { Status } from "./OperationsPanels";
import { statusText, type Audit, type Movement } from "./operations";

const QrScanner = lazy(async () => ({ default: (await import("./QrScanner")).QrScanner }));
const number = new Intl.NumberFormat("ko-KR");
const dateFormat = new Intl.DateTimeFormat("ko-KR", { timeZone: "Asia/Seoul", dateStyle: "medium" });
const timeFormat = new Intl.DateTimeFormat("ko-KR", {
  timeZone: "Asia/Seoul", month: "numeric", day: "numeric", hour: "2-digit", minute: "2-digit",
});
const colors = ["#159887", "#4e80bb", "#8c70ba", "#db9760", "#97a8b6"];

export function Heading({ title, description, children }: { title: string; description?: string; children?: ReactNode }) {
  return <div className="page-heading"><div><h1>{title}</h1>{description && <p>{description}</p>}</div>
    {children && <div className="actions">{children}</div>}</div>;
}

function CardHeading({ title, subtitle, children }: { title: string; subtitle?: string; children?: ReactNode }) {
  return <div className="card-heading"><div><h2>{title}</h2>{subtitle && <p>{subtitle}</p>}</div>{children}</div>;
}

function Metric({ label, value, unit, foot, icon, tone, onClick }: {
  label: string; value: number | null; unit: string; foot?: string; icon: IconName; tone?: string; onClick?: () => void;
}) {
  const contents = <>
    <span className="metric-head"><span className={`tile-icon ${tone ?? ""}`}><Icon name={icon} /></span>{label}</span>
    <span className="number">{value === null ? "—" : <>{number.format(value)}<small>{unit}</small></>}</span>
    {foot && <span className="metric-foot">{foot}</span>}
  </>;
  return onClick ? <button className="metric" type="button" onClick={onClick}>{contents}</button>
    : <div className="metric">{contents}</div>;
}

export function Dashboard({ summary, changes, department, manage, browse, audit, issues, history, intake, notices }: {
  summary: DashboardSummary; changes: Movement[]; department: string; manage: boolean;
  browse: () => void; audit: () => void; issues: () => void; history: () => void; intake: () => void; notices: () => void;
}) {
  const { total_assets: total, active_assets: active, audit_checked: checked, audit_matched: matched } = summary;
  const series = Object.entries(summary.categories).sort((first, second) => second[1] - first[1]);
  let offset = 0;
  const segments = series.map(([, count], index) => {
    const start = offset;
    offset += 100 * count / total;
    return `${colors[index % colors.length]} ${start}% ${offset}%`;
  });
  return <>
    <div className="urgent"><Icon name="meg" /><strong>긴급 공지</strong><span className="urgent-value">—</span>
      <ViewLink onClick={notices}>공지 보기</ViewLink></div>
    <Heading title="자산관리 대시보드" description="사내 자산의 현황과 주요 변동 사항을 확인하세요.">
      <span className="date-label"><Icon name="calendar" />{dateFormat.format(new Date())} 기준</span>
      <span className="scope-label">{department}</span>
      {manage && <button className="action-button" type="button" onClick={intake}><Icon name="plus" />자산 등록</button>}
    </Heading>
    <div className="grid-metrics">
      <Metric label="전체 자산" value={total} unit="개" icon="box" foot={`${number.format(active)}개 사용 중`} onClick={browse} />
      <Metric label="실사 일치율" value={checked && matched !== null ? Math.round(100 * matched / checked) : null}
        unit="%" icon="audit" tone="blue" foot={checked === null ? undefined : `${matched} / ${checked}개 일치`}
        onClick={manage ? audit : undefined} />
      <Metric label="실사 불일치" value={summary.audit_issues} unit="건" icon="warning" tone="orange"
        foot={summary.audit_issues === null ? undefined : "최근 실사 확인 결과"} onClick={manage ? issues : undefined} />
      <Metric label="이번 주 변동" value={summary.weekly_changes} unit="건" icon="swap" tone="purple"
        foot={manage ? "자산·재고 변동 기록" : undefined} onClick={manage ? history : undefined} />
    </div>
    <div className={`two-up ${manage ? "" : "single"}`}>
      <section className="card">
        <CardHeading title="자산 구성" subtitle="분류별 자산 비율"><ViewLink onClick={browse}>자산 현황</ViewLink></CardHeading>
        <div className="chart-body">
          <div className="donut" style={segments.length ? { background: `conic-gradient(${segments.join(",")})` } : undefined}>
            <div className="donut-center"><b>{number.format(total)}</b><small>전체 자산</small></div>
          </div>
          <div className="chart-legend">{series.length ? series.map(([name, count], index) =>
            <div className="legend-item" key={name}><i style={{ backgroundColor: colors[index % colors.length] }} />
              <span>{name}</span><b>{number.format(count)}개</b><small>{(100 * count / total).toFixed(1)}%</small></div>)
            : <p className="muted">분류 데이터가 없습니다.</p>}</div>
        </div>
        <div className="chart-footer"><span>개별 자산 기준</span><span>{department}</span></div>
      </section>
      {manage && <section className="card">
        <CardHeading title="최근 변동 사항" subtitle="입고 및 재고 수불 기록"><ViewLink onClick={history}>전체 보기</ViewLink></CardHeading>
        <EventList rows={changes.slice(0, 4)} />
      </section>}
    </div>
    <section className="card table-card">
      <CardHeading title="핵심 자산" subtitle="주요 관리 대상 자산"><ViewLink onClick={browse}>자산 목록 보기</ViewLink></CardHeading>
      <AssetTable rows={[]} empty="지정된 핵심 자산이 없습니다." />
    </section>
  </>;
}

export function ViewLink({ children, onClick }: { children: ReactNode; onClick: () => void }) {
  return <button className="text-button view-link" onClick={onClick}>{children}<Icon name="arrow" /></button>;
}

function EventList({ rows }: { rows: Movement[] }) {
  if (!rows.length) return <p className="empty">기록된 변동이 없습니다.</p>;
  return <ul className="changes-list">{rows.map((row) => <li className="event" key={row.id}>
    <span className={`tile-icon ${row.kind === "receipt" ? "" : "purple"}`}><Icon name={row.kind === "receipt" ? "box" : "swap"} /></span>
    <span><b className="event-title">{statusText[row.kind] ?? row.kind}{row.details.quantity != null && ` · ${number.format(row.details.quantity)}개`}</b>
      {row.details.note && <small>{row.details.note}</small>}</span>
    <time dateTime={row.created_at}>{timeFormat.format(new Date(row.created_at))}</time>
  </li>)}</ul>;
}

export function ChangeView({ rows }: { rows: Movement[] }) {
  const [query, setQuery] = useState("");
  const [kind, setKind] = useState("");
  const visible = rows.filter((row) => (!kind || row.kind === kind) && (
    `${statusText[row.kind] ?? row.kind} ${row.details.note ?? ""}`.includes(query.trim())
  ));
  return <section className="card"><div className="filters">
    <input type="search" aria-label="변동 이력 검색" placeholder="변동 유형·사유 검색" value={query} onChange={(event) => setQuery(event.target.value)} />
    <select aria-label="변동 유형" value={kind} onChange={(event) => setKind(event.target.value)}>
      <option value="">전체 유형</option>{Array.from(new Set(rows.map((row) => row.kind))).map((key) =>
        <option value={key} key={key}>{statusText[key] ?? key}</option>)}
    </select></div><EventList rows={visible} /></section>;
}

function AssetTable({ rows, pick, empty }: { rows: Asset[]; pick?: (asset: Asset) => void; empty: string }) {
  return <><div className="table-wrap"><table>
    <thead><tr><th>자산명</th><th>자산 코드</th><th>관리 부서</th><th>보관 위치</th><th>상태</th><th>상세</th></tr></thead>
    <tbody>{rows.map((asset) => <tr key={asset.id}>
      <td>{pick ? <button className="asset-link" onClick={() => pick(asset)}><Icon name="box" className="asset-icon" />{asset.name}</button>
        : asset.name}</td>
      <td className="asset-code">{asset.code}</td><td>{asset.department}</td><td>{asset.location}</td>
      <td><Status value={asset.status} /></td><td>{pick && <ViewLink onClick={() => pick(asset)}>상세</ViewLink>}</td>
    </tr>)}</tbody>
  </table></div>{!rows.length && <p className="empty">{empty}</p>}</>;
}

export function AssetView({ token, rows, search }: { token: string; rows: Asset[]; search: string }) {
  const [query, setQuery] = useState(search);
  const [status, setStatus] = useState("");
  const [filtered, setFiltered] = useState<Asset[] | null>(null);
  const [qr, setQr] = useState("");
  const [scanning, setScanning] = useState(false);
  const [error, setError] = useState("");
  const [found, setFound] = useState<Asset | null>(null);
  useEffect(() => {
    if (!search) return;
    let active = true;
    request<Asset[]>(`/assets?q=${encodeURIComponent(search)}`, token).then(
      (result) => { if (active) setFiltered(result); },
      (reason) => { if (active) setError(String(reason)); },
    );
    return () => { active = false; };
  }, [search, token]);
  const lookup = useCallback(async (value: string) => {
    setQr(value);
    setScanning(false);
    setError("");
    setFound(null);
    try { setFound(await request<Asset>(`/assets/qr/${encodeURIComponent(value.trim())}`, token)); }
    catch (reason) { setError(String(reason)); }
  }, [token]);

  const loaded = filtered ?? rows;
  const visible = loaded.filter((row) => (!status || row.status === status) && (
    !query.trim() || [row.name, row.code, row.location].some((field) => field.toLowerCase().includes(query.trim().toLowerCase()))
  ));
  return <div className="stack">
    <section className="card">
      <form className="filters" onSubmit={async (event) => {
        event.preventDefault();
        setError("");
        try { setFiltered(await request<Asset[]>(`/assets?q=${encodeURIComponent(query.trim())}`, token)); }
        catch (reason) { setError(String(reason)); }
      }}>
        <input aria-label="자산 검색" type="search" placeholder="자산명 또는 코드 검색" value={query}
          maxLength={128} onChange={(event) => { setQuery(event.target.value); setFiltered(null); }} />
        <select aria-label="분류" disabled><option>전체 분류</option></select>
        <select aria-label="자산 상태" value={status} onChange={(event) => setStatus(event.target.value)}>
          <option value="">전체 상태</option>{Array.from(new Set(loaded.map((row) => row.status))).map((key) =>
            <option value={key} key={key}>{statusText[key] ?? key}</option>)}
        </select><button type="submit" className="secondary">검색</button>
      </form>
      <AssetTable rows={visible} pick={setFound} empty="조건에 맞는 자산이 없습니다." />
    </section>
    <section className="panel">
      <h2>QR 자산 조회</h2>
      <form className="row" onSubmit={(event) => { event.preventDefault(); void lookup(qr); }}>
        <input aria-label="QR 값" value={qr} onChange={(event) => setQr(event.target.value)} placeholder="QR 값 입력" required />
        <button>조회</button><button className="secondary" type="button" onClick={() => setScanning(!scanning)}>
          {scanning ? "카메라 닫기" : "카메라로 스캔"}</button>
      </form>
      {scanning && <Suspense fallback={<p>카메라 준비 중…</p>}><QrScanner onScan={lookup} /></Suspense>}
      {error && <p className="error" role="alert">{error}</p>}
    </section>
    {found && <section className="panel" aria-label="자산 상세">
      <div className="section-heading"><h2>{found.name}</h2><Status value={found.status} /></div>
      <dl className="details">
        {[["자산 코드", found.code], ["관리 부서", found.department], ["보관 위치", found.location],
          ["품목 코드", found.item_code], ["시리얼 번호", found.serial]].map(([label, value]) =>
          <div key={label}><dt>{label}</dt><dd>{value ?? "—"}</dd></div>)}
      </dl>
    </section>}
  </div>;
}

export function IssueView({ audits }: { audits: Audit[] }) {
  const rows = audits.flatMap((audit) => audit.targets
    .filter((target) => target.result === "missing" || target.result === "mismatch")
    .map((target) => ({ ...target, title: audit.title })));
  return <section className="card"><div className="table-wrap"><table><thead><tr>
    <th>실사 회차</th><th>대상</th><th>장부 위치</th><th>확인 위치</th><th>결과</th>
  </tr></thead><tbody>{rows.map((row) => <tr key={row.id}><td>{row.title}</td><td>{row.label}</td>
    <td>{row.expected_location}</td><td>{row.observed_location}</td><td><Status value={row.result} /></td></tr>)}
  </tbody></table></div>{!rows.length && <p className="empty">표시할 불일치 기록이 없습니다.</p>}</section>;
}

export function EmptyTable({ title, headers, message }: { title: string; headers: string[]; message: string }) {
  return <section className="card"><CardHeading title={title} /><div className="table-wrap">
    <table><thead><tr>{headers.map((header) => <th key={header}>{header}</th>)}</tr></thead><tbody /></table>
  </div><p className="empty">{message}</p></section>;
}

export function LocationView() {
  return <div className="floor-layout">
    <section className="panel"><div className="section-heading"><h2>층별 도면</h2>
      <select className="floor-select" aria-label="층 선택" disabled><option>층 선택</option></select></div>
      <div className="floor"><p className="muted">등록된 도면이 없습니다.</p></div>
    </section>
    <section className="panel"><h2>구역별 자산</h2><p className="empty">선택된 구역이 없습니다.</p></section>
  </div>;
}
