export type Role = "asset_manager" | "purchasing" | "vendor" | "employee";
export type User = { sub: string; role: Role; department: string };
export type IntakeLine = {
  id: string; item_code: string; name: string; tracking: "individual" | "quantity";
  location: string; submitted_quantity: number; approved_quantity: number | null;
  received_quantity: number | null; accepted_quantity: number | null;
  labels: string[]; variance_note: string | null;
};
export type Intake = {
  id: string; document_number: string; vendor_id: string; department: string;
  status: string; review_note: string | null; signer_name: string | null; lines: IntakeLine[];
};
export type AuditTarget = {
  id: string; kind: "individual" | "quantity"; label: string;
  expected_location: string; expected_quantity: number; observed_quantity: number | null;
  observed_location: string | null; result: string;
};
export type Audit = {
  id: string; title: string; assigned_to: string; status: string;
  scheduled_for: string | null; targets: AuditTarget[];
};
export type Stock = {
  id: string; item_code: string; name: string; location: string; quantity: number; safety_stock: number;
};
export type Movement = { id: string; kind: string; actor: string; created_at: string; details: { quantity?: number; note?: string } };
export type Notice = { id: string; title: string; reference_id: string; created_at: string; read_at: string | null };
export type Inbox = { unread: number; items: Notice[] };

export const roleLabels: Record<Role, string> = {
  asset_manager: "부서 담당자", purchasing: "구매 담당자", vendor: "외부업체", employee: "일반 임직원",
};

export const statusText: Record<string, string> = {
  submitted: "검토 대기", approved: "등록 승인", rejected: "반려", inspected: "검수 완료",
  signed: "서명 완료", received: "입고 확정",
  scheduled: "예정", running: "진행 중", review: "검토 중", completed: "완료",
  unchecked: "미확인", missing: "미발견", mismatch: "불일치", matched: "일치",
  stored: "보관", receipt: "입고", issue: "지급", consume: "공정 소모",
};
