import { lazy, Suspense, useState, type FormEvent } from "react";
import { request } from "./api";
import { statusText, type Audit, type Inbox, type Intake, type Movement, type Stock, type User } from "./operations";

const QrScanner = lazy(async () => ({ default: (await import("./QrScanner")).QrScanner }));
type Action = (work: () => Promise<unknown>) => Promise<void>;

function value(form: FormData, name: string) {
  return String(form.get(name) ?? "").trim();
}

export function Status({ value }: { value: string }) {
  const tone = ["received", "completed", "matched", "approved"].includes(value)
    ? "success" : ["rejected", "mismatch", "missing"].includes(value) ? "danger" : "";
  return <span className={`status ${tone}`}>{statusText[value] ?? value}</span>;
}

export function IntakePanel({ items, user, token, action }: {
  items: Intake[]; user: User; token: string; action: Action;
}) {
  const [selected, setSelected] = useState("");
  const [lineCount, setLineCount] = useState(1);
  const [showForm, setShowForm] = useState(false);
  const item = items.find((entry) => entry.id === selected) ?? items[0];
  const vendor = user.role === "vendor";

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    void action(async () => {
      const created = await request<Intake>("/intakes", token, {
        document_number: value(form, "document"),
        department: value(form, "department"),
        lines: Array.from({ length: lineCount }, (_, index) => ({
          item_code: value(form, `code-${index}`), name: value(form, `name-${index}`),
          quantity: Number(value(form, `qty-${index}`)), tracking: value(form, `tracking-${index}`),
          location: value(form, `location-${index}`),
        })),
      });
      setSelected(created.id);
      setShowForm(false);
      setLineCount(1);
    });
  }

  async function printLabel(tokenId: string, requestId: string) {
    const response = await fetch(`/api/intakes/${requestId}/labels/${tokenId}`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!response.ok) throw new Error("QR 라벨을 가져올 수 없습니다.");
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = `QR-${tokenId.slice(0, 8)}.png`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(url), 10_000);
  }

  return <div className="stack">
    <section className="panel">
      <div className="section-heading"><h2>납품 요청 목록</h2>{vendor && <button onClick={() => setShowForm(!showForm)}>
        {showForm ? "양식 닫기" : "납품 등록"}
      </button>}</div>
      {showForm && vendor && <form className="stack form-block" onSubmit={submit}>
        <div className="form-grid">
          <label>명세서 번호<input name="document" maxLength={80} required /></label>
          <label>관리 부서 코드<input name="department" defaultValue="operations" maxLength={64} required /></label>
        </div>
        {Array.from({ length: lineCount }, (_, index) => <fieldset key={index}>
          <legend>품목 {index + 1}</legend>
          <div className="form-grid">
            <label>품목 코드<input name={`code-${index}`} maxLength={64} required /></label>
            <label>품목명<input name={`name-${index}`} maxLength={128} required /></label>
            <label>관리 방식<select name={`tracking-${index}`}><option value="individual">개별 자산</option><option value="quantity">수량 재고</option></select></label>
            <label>제출 수량<input name={`qty-${index}`} type="number" min={1} max={1000000} defaultValue={1} required /></label>
            <label>입고 위치<input name={`location-${index}`} maxLength={128} required /></label>
          </div>
        </fieldset>)}
        <div className="actions"><button type="button" className="secondary" disabled={lineCount >= 25} onClick={() => setLineCount(lineCount + 1)}>품목 추가</button>
          {lineCount > 1 && <button type="button" className="secondary" onClick={() => setLineCount(lineCount - 1)}>마지막 품목 삭제</button>}
          <button>등록 요청 보내기</button></div>
      </form>}
      <div className="table-wrap"><table><thead><tr><th>명세서</th><th>관리 부서</th><th>품목</th><th>진행 상태</th></tr></thead>
        <tbody>{items.map((row) => <tr key={row.id}>
          <td><button className="text-button" onClick={() => setSelected(row.id)}>{row.document_number}</button></td>
          <td>{row.department}</td><td>{row.lines.length}건</td><td><Status value={row.status} /></td>
        </tr>)}</tbody></table></div>
      {items.length === 0 && <p className="empty">접수된 납품 요청이 없습니다.</p>}
    </section>
    {item && <section className="panel" key={`${item.id}:${item.status}`}>
      <div className="section-heading"><h2>{item.document_number}</h2><Status value={item.status} /></div>
      <div className="table-wrap"><table><thead><tr><th>품목</th><th>제출</th><th>승인</th><th>수령</th><th>합격</th><th>QR</th></tr></thead>
        <tbody>{item.lines.map((line) => <tr key={line.id}>
          <td>{line.name}<small>{line.location}</small></td><td>{line.submitted_quantity}</td><td>{line.approved_quantity ?? "—"}</td>
          <td>{line.received_quantity ?? "—"}</td><td>{line.accepted_quantity ?? "—"}</td>
          <td>{line.labels.slice(0, item.status === "received" ? line.accepted_quantity ?? 0 : undefined).map((label, index) =>
            <button key={label} className="text-button qr-link" onClick={() => void action(() => printLabel(label, item.id))}>QR {index + 1}</button>)}</td>
        </tr>)}</tbody></table></div>
      {item.review_note && <p>검토 의견 · {item.review_note}</p>}
      {item.signer_name && <p>인수 확인자 · {item.signer_name}</p>}
      {!vendor && item.status === "submitted" && <form className="stack form-block" onSubmit={(event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        const submitter = (event.nativeEvent as SubmitEvent).submitter as HTMLButtonElement;
        void action(() => request(`/intakes/${item.id}/review`, token, {
          decision: submitter?.value || "approve", note: value(form, "note") || null,
          quantities: Object.fromEntries(item.lines.map((line) => [line.id, Number(value(form, line.id))])),
        }));
      }}>
        <div className="form-grid">{item.lines.map((line) =>
          <label key={line.id}>{line.name} 승인 수량<input name={line.id} type="number" min={0} max={line.submitted_quantity} defaultValue={line.submitted_quantity} required /></label>)}</div>
        <label>검토 의견 또는 반려 사유<input name="note" maxLength={500} /></label>
        <div className="actions"><button value="approve">등록 승인</button><button value="reject" className="secondary">반려</button></div>
      </form>}
      {!vendor && ["approved", "inspected"].includes(item.status) && <form className="stack form-block" onSubmit={(event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        void action(() => request(`/intakes/${item.id}/inspect`, token, {
          lines: item.lines.map((line) => ({
            line_id: line.id, received: Number(value(form, `r-${line.id}`)), accepted: Number(value(form, `a-${line.id}`)),
            note: value(form, `n-${line.id}`) || null, serials: value(form, `s-${line.id}`).split(",").map((part) => part.trim()).filter(Boolean),
          })),
        }));
      }}>
        {item.lines.map((line) => <fieldset key={line.id}><legend>{line.name} 현장 검수</legend><div className="form-grid">
          <label>수령 수량<input name={`r-${line.id}`} type="number" min={0} max={1000000} defaultValue={line.received_quantity ?? line.approved_quantity ?? 0} required /></label>
          <label>합격 수량<input name={`a-${line.id}`} type="number" min={0} max={line.approved_quantity ?? 0} defaultValue={line.accepted_quantity ?? line.approved_quantity ?? 0} required /></label>
          <label>수량 차이 사유<input name={`n-${line.id}`} maxLength={500} defaultValue={line.variance_note ?? ""} /></label>
          {line.tracking === "individual" && <label>시리얼 번호 · 쉼표 구분<input name={`s-${line.id}`} /></label>}
        </div></fieldset>)}
        <div><button>검수 결과 저장</button></div>
      </form>}
      {vendor && item.status === "inspected" && <form className="stack form-block" onSubmit={(event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        void action(() => request(`/intakes/${item.id}/sign`, token, { name: value(form, "name") }));
      }}><label>인수 확인자 이름<input name="name" maxLength={80} required /></label><div><button>인수 내용 확인</button></div></form>}
      {!vendor && item.status === "signed" && <div className="form-block"><button onClick={() => void action(() => request(`/intakes/${item.id}/receive`, token, {}))}>입고 확정</button></div>}
    </section>}
  </div>;
}

export function AuditPanel({ items, user, token, action, analyze }: {
  items: Audit[]; user: User; token: string; action: Action; analyze: (id: string) => void;
}) {
  const [selected, setSelected] = useState("");
  const [camera, setCamera] = useState(false);
  const [qr, setQr] = useState("");
  const [location, setLocation] = useState("");
  const item = items.find((row) => row.id === selected) ?? items[0];
  const checked = item?.targets.filter((target) => target.observed_quantity !== null).length ?? 0;
  const canObserve = item?.status === "running" && item.assigned_to === user.sub;

  function scan(tokenValue: string) {
    if (!item) return;
    setCamera(false);
    void action(() => request(`/audits/${item.id}/observe`, token, { qr_token: tokenValue.trim(), quantity: 1, location }));
  }

  return <div className="stack">
    <section className="panel">
      <h2>실사 일정</h2>
      <form className="form-grid align-end" onSubmit={(event) => {
        event.preventDefault();
        const form = new FormData(event.currentTarget);
        void action(async () => {
          const scheduled = value(form, "schedule");
          const audit = await request<Audit>("/audits", token, {
            title: value(form, "title"), location: value(form, "location") || null,
            assigned_to: value(form, "assignee") || null,
            scheduled_for: scheduled ? new Date(scheduled).toISOString() : null,
          });
          setSelected(audit.id);
        });
      }}>
        <label>회차명<input name="title" maxLength={128} placeholder="정기 실사" required /></label>
        <label>대상 위치<input name="location" maxLength={128} placeholder="비우면 부서 전체" /></label>
        <label>예정 시각<input type="datetime-local" name="schedule" /></label>
        <label>실사 담당자<select name="assignee">
          <option value="">내 계정</option>
          {user.role === "purchasing" && <option value="demo-manager">부서 담당자 · 샘플</option>}
        </select></label>
        <div><button>실사 회차 만들기</button></div>
      </form>
      {items.length > 0 && <label className="form-block">실사 회차<select value={item?.id ?? ""} onChange={(event) => {
        setSelected(event.target.value); setCamera(false); setQr(""); setLocation("");
      }}>{items.map((row) => <option key={row.id} value={row.id}>{row.title} · {statusText[row.status]}</option>)}</select></label>}
    </section>
    {item && <section className="panel" key={item.id}>
      <div className="section-heading"><h2>{item.title}</h2><Status value={item.status} /></div>
      <div className="audit-progress">
        <div><h3>실사 진행률</h3>
          {item.targets.length > 0
            ? <><p>확인 완료 <b>{checked} / {item.targets.length}개</b></p>
              <progress aria-label="실사 진행률" value={checked} max={item.targets.length} /></>
            : <p>—</p>}
        </div>
        <div><h3>실사 예정 시각</h3><p>{item.scheduled_for
          ? new Date(item.scheduled_for).toLocaleString("ko-KR", { timeZone: "Asia/Seoul" }) : "—"}</p></div>
      </div>
      <div className="actions">
        {item.assigned_to === user.sub && item.status === "scheduled" && <button onClick={() => void action(() => request(`/audits/${item.id}/start`, token, {}))}>실사 시작</button>}
        {canObserve && <button className="secondary" onClick={() => void action(() => request(`/audits/${item.id}/finish`, token, {}))}>결과 제출</button>}
        {item.status === "review" && user.role === "purchasing" && <button onClick={() => void action(() => request(`/audits/${item.id}/approve`, token, {}))}>실사 확정</button>}
        {["review", "completed"].includes(item.status) && <button className="secondary" onClick={() => analyze(item.id)}>실사 분석 요청</button>}
      </div>
      {canObserve && <form className="form-grid form-block align-end" onSubmit={(event) => { event.preventDefault(); scan(qr); }}>
        <label>현장 위치<input value={location} onChange={(event) => setLocation(event.target.value)} required /></label>
        <label>QR 값<input value={qr} onChange={(event) => setQr(event.target.value)} required /></label>
        <div className="actions"><button type="submit">확인 기록</button><button type="button" className="secondary" disabled={!location.trim()} onClick={() => setCamera(!camera)}>{camera ? "카메라 닫기" : "QR 스캔"}</button></div>
      </form>}
      {camera && canObserve && <Suspense fallback={<p>카메라 준비 중…</p>}><QrScanner onScan={scan} /></Suspense>}
      {item.targets.length > 0 && <>
        <div className="table-wrap"><table><thead><tr><th>대상</th><th>장부</th><th>현장</th><th>판정</th>{canObserve && <th>기록</th>}</tr></thead>
          <tbody>{item.targets.map((target) => <tr key={target.id}>
            <td>{target.label}</td><td>{target.expected_quantity} · {target.expected_location}</td>
            <td>{target.observed_quantity ?? "—"} {target.observed_location}</td><td><Status value={target.result} /></td>
            {canObserve && <td>{target.observed_quantity === null && <form className="inline-form" onSubmit={(event) => {
              event.preventDefault();
              const form = new FormData(event.currentTarget);
              const quantity = Number(value(form, "quantity"));
              void action(() => request(`/audits/${item.id}/observe`, token, {
                target_id: target.id, quantity, location: quantity > 0 ? value(form, "location") : null,
              }));
            }}><input aria-label={`${target.label} 확인 수량`} name="quantity" type="number" min={0} max={target.kind === "individual" ? 1 : 1000000} defaultValue={target.expected_quantity} required />
              <input aria-label={`${target.label} 확인 위치`} name="location" defaultValue={target.expected_location} /><button>저장</button></form>}</td>}
          </tr>)}</tbody></table></div>
      </>}
    </section>}
  </div>;
}

export function StockPanel({ rows, token, action }: { rows: Stock[]; token: string; action: Action }) {
  return <section className="panel"><h2>품목별 현재고</h2><div className="table-wrap">
    <table><thead><tr><th>품목</th><th>보관 위치</th><th>현재고</th><th>안전재고</th><th>지급·소모 기록</th></tr></thead>
      <tbody>{rows.map((row) => <tr key={row.id}><td>{row.name}<small>{row.item_code}</small></td><td>{row.location}</td><td>{row.quantity}</td><td>
        <form className="inline-form" onSubmit={(event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          void action(() => request(`/stock/${row.id}/threshold`, token, { quantity: Number(value(form, "threshold")) }));
        }}><input aria-label="안전재고 기준" name="threshold" type="number" min={0} max={1000000} defaultValue={row.safety_stock} required /><button className="secondary">저장</button></form>
      </td>
        <td><form className="inline-form" onSubmit={(event) => {
          event.preventDefault();
          const form = new FormData(event.currentTarget);
          void action(() => request(`/stock/${row.id}/use`, token, {
            operation_id: crypto.randomUUID(), quantity: Number(value(form, "quantity")), note: value(form, "note"), purpose: value(form, "purpose"),
          }));
        }}>
          <select aria-label="변동 유형" name="purpose"><option value="issue">지급</option><option value="consume">공정 소모</option></select>
          <input aria-label="출고 수량" name="quantity" type="number" min={1} max={row.quantity} required />
          <input aria-label="처리 사유" name="note" maxLength={500} placeholder="처리 사유" required />
          <button disabled={row.quantity === 0}>기록</button>
        </form></td></tr>)}</tbody></table>
    </div>{rows.length === 0 && <p className="empty">입고 확정된 수량 재고가 없습니다.</p>}</section>;
}

export function Movements({ rows }: { rows: Movement[] }) {
  return <section className="panel"><h2>확정 변동 이력</h2><div className="table-wrap"><table>
    <thead><tr><th>유형</th><th>수량</th><th>처리자</th><th>처리 시각</th><th>사유</th></tr></thead>
    <tbody>{rows.map((row) => <tr key={row.id}><td><Status value={row.kind} /></td><td>{row.details.quantity ?? "—"}</td>
      <td>{row.actor}</td><td>{new Date(row.created_at).toLocaleString("ko-KR")}</td><td>{row.details.note ?? "—"}</td></tr>)}</tbody>
  </table></div>{!rows.length && <p className="empty">기록된 변동이 없습니다.</p>}</section>;
}

export function InboxPanel({ inbox, token, action }: { inbox: Inbox; token: string; action: Action }) {
  return <section className="panel"><div className="section-heading"><h2>받은 알림</h2><span className="status">미읽음 {inbox.unread}건</span></div>
    {inbox.items.map((notice) => <div className="notice" key={notice.id}>
      <span><b>{notice.title}</b><small>{new Date(notice.created_at).toLocaleString("ko-KR")}</small></span>
      {!notice.read_at ? <button className="secondary" onClick={() => void action(() => request(`/notifications/${notice.id}/read`, token, {}))}>읽음 처리</button> : <span className="muted">읽음</span>}
    </div>)}
    {!inbox.items.length && <p className="empty">받은 알림이 없습니다.</p>}
  </section>;
}
