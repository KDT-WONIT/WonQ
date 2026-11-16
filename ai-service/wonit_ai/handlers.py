from contracts.messages import JobKind


def chatbot(context: dict) -> dict:
    assets = context["assets"]
    return {
        "mode": "scaffold",
        "message": f"현재 권한 범위에서 조회 예시 자산 {len(assets)}건을 가져왔습니다.",
        "assets": assets,
    }


def report(context: dict) -> dict:
    return {
        "mode": "scaffold",
        "message": "보고서에 사용할 부서 자산 수를 집계했습니다.",
        "asset_count": context["asset_count"],
    }


def inspection(context: dict) -> dict:
    if "audit" in context:
        exceptions = [row for row in context["audit"] if row["result"] != "matched"]
        return {
            "mode": "rules",
            "message": "불일치·미확인 건의 실제 위치와 최근 이동 기록을 확인하세요.",
            "exceptions": exceptions,
        }
    return {
        "mode": "scaffold",
        "message": "실사 이력과 원인 분석을 연결할 단계입니다.",
        "asset": context["asset"],
    }


def monitoring(context: dict) -> dict:
    shortages = [row for row in context.get("stock", []) if row["quantity"] < row["safety_stock"]]
    return {
        "mode": "rules",
        "message": f"현재 안전재고 미달 품목 {len(shortages)}건",
        "shortages": shortages,
    }


HANDLERS = {
    JobKind.CHATBOT: chatbot,
    JobKind.REPORT: report,
    JobKind.INSPECTION: inspection,
    JobKind.MONITORING: monitoring,
}
