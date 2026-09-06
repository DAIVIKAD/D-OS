from __future__ import annotations

import csv
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
from io import BytesIO, StringIO
from typing import Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.core.templates import templates
from app.core.view import context
from app.firebase.auth import require_user
from app.services import firestore_service as store
from app.services.finance import (
    as_float,
    chart_data,
    current_month_range,
    dashboard_data,
    prefetch_data,
    to_decimal,
    tx_date,
)
from app.services.profile_service import get_categories
from app.utils.formatting import optional_date

router = APIRouter()

STANDARD_PAYMENT_METHODS = ["UPI", "Cash", "Card", "Bank Transfer", "Net Banking"]


def get_report_data(
    user: dict[str, Any],
    start: str | None = None,
    end: str | None = None,
    type_filter: str | None = None,
    category_id: str | None = None,
    payment_method: str | None = None,
) -> dict[str, Any]:
    """Compile filtered data and financial metrics for the Report Builder preview and exports."""
    today = date.today()
    default_start, _ = current_month_range(today)
    start_date = optional_date(start) or default_start
    end_date = optional_date(end) or today

    data = prefetch_data(user, include_investments=False)
    raw_transactions = data["transactions"]
    all_debts = data["debts"]

    # Gather distinct payment methods across all transactions
    user_methods = set(STANDARD_PAYMENT_METHODS)
    for tx in raw_transactions:
        pm = str(tx.get("payment_method", "")).strip()
        if pm:
            user_methods.add(pm)
    all_payment_methods = sorted(user_methods)

    user_categories = get_categories(user)
    cat_map = {str(c["id"]): c["name"] for c in user_categories}

    # Normalize type filter
    norm_type = (type_filter or "").strip().lower()
    if norm_type in ("all", ""):
        norm_type = "all"

    # Filter transactions
    filtered_transactions: list[dict[str, Any]] = []
    for tx in raw_transactions:
        d = tx_date(tx)
        if start_date and d < start_date:
            continue
        if end_date and d > end_date:
            continue

        raw_kind = str(tx.get("type", "")).lower()
        if norm_type in ("income", "expense") and raw_kind != norm_type:
            continue

        if category_id and category_id.strip() and category_id != "all":
            tx_cat_id = str(tx.get("category_id", ""))
            tx_cat_name = str((tx.get("category") or {}).get("name", ""))
            if tx_cat_id != category_id and tx_cat_name != category_id:
                continue

        if payment_method and payment_method.strip() and payment_method != "all":
            pm_needle = payment_method.strip().lower()
            tx_pm = str(tx.get("payment_method", "")).lower()
            if pm_needle not in tx_pm:
                continue

        filtered_transactions.append(tx)

    # Sort transactions descending by date
    filtered_transactions.sort(key=lambda t: tx_date(t), reverse=True)

    # Calculate Income & Expense KPIs strictly from matching transactions
    matching_income = [t for t in filtered_transactions if str(t.get("type", "")).lower() == "income"]
    matching_expense = [t for t in filtered_transactions if str(t.get("type", "")).lower() == "expense"]

    total_income = sum(to_decimal(t.get("amount")) for t in matching_income)
    total_expense = sum(to_decimal(t.get("amount")) for t in matching_expense)
    available_balance = total_income - total_expense

    # Debts / Liabilities & Receivables
    borrowed_debts = [d for d in all_debts if d.get("direction") == "borrow"]
    lent_debts = [d for d in all_debts if d.get("direction") == "lend"]
    settled_debts = [d for d in all_debts if d.get("status") == "settled"]

    total_borrowed = sum(to_decimal(d.get("amount")) for d in borrowed_debts)
    total_lent = sum(to_decimal(d.get("amount")) for d in lent_debts)
    total_repayments = sum(to_decimal(d.get("amount")) for d in settled_debts)

    # Transfers (identified by payment method or note)
    total_transfers = sum(
        to_decimal(t.get("amount"))
        for t in filtered_transactions
        if "transfer" in str(t.get("payment_method", "")).lower()
        or "transfer" in str(t.get("note", "")).lower()
    )

    # Category breakdown (for expenses or matching transactions)
    cat_counts: dict[str, int] = defaultdict(int)
    cat_totals: dict[str, Decimal] = defaultdict(lambda: Decimal("0"))
    cat_icons: dict[str, str] = {}

    target_for_breakdown = matching_income if norm_type == "income" else matching_expense
    if norm_type == "all" and not matching_expense and matching_income:
        target_for_breakdown = matching_income

    for t in target_for_breakdown:
        cat_info = t.get("category") or {}
        name = str(cat_info.get("name") or cat_map.get(str(t.get("category_id", "")), "Uncategorized"))
        icon = str(cat_info.get("icon") or "◇")
        cat_counts[name] += 1
        cat_totals[name] += to_decimal(t.get("amount"))
        cat_icons[name] = icon

    base_sum = total_income if norm_type == "income" else total_expense
    category_breakdown: list[dict[str, Any]] = []
    for name, amt in sorted(cat_totals.items(), key=lambda item: item[1], reverse=True):
        pct = (amt / base_sum * Decimal("100")) if base_sum > Decimal("0") else Decimal("0")
        category_breakdown.append({
            "name": name,
            "icon": cat_icons.get(name, "◇"),
            "count": cat_counts[name],
            "amount": amt,
            "pct": f"{pct:.1f}%",
        })

    period_str = f"{start_date.strftime('%d %b %Y')} to {end_date.strftime('%d %b %Y')}"

    return {
        "start_date": start_date,
        "end_date": end_date,
        "period_str": period_str,
        "type_filter": norm_type,
        "category_id": category_id or "all",
        "payment_method": payment_method or "all",
        "all_categories": user_categories,
        "all_payment_methods": all_payment_methods,
        "matching_transactions": filtered_transactions,
        "total_income": total_income,
        "total_expense": total_expense,
        "available_balance": available_balance,
        "total_borrowed": total_borrowed,
        "total_lent": total_lent,
        "total_repayments": total_repayments,
        "total_transfers": total_transfers,
        "category_breakdown": category_breakdown,
        "transaction_count": len(filtered_transactions),
        "currency": str(user.get("currency", "₹")),
    }


@router.get("/reports")
def reports_page(
    request: Request,
    start: str | None = None,
    end: str | None = None,
    type: str | None = None,
    category_id: str | None = None,
    payment_method: str | None = None,
    user: dict = Depends(require_user),
):
    data = prefetch_data(user, include_investments=False)
    report = get_report_data(
        user,
        start=start,
        end=end,
        type_filter=type,
        category_id=category_id,
        payment_method=payment_method,
    )

    return templates.TemplateResponse(
        "pages/reports.html",
        context(
            request,
            user,
            page_title="Reports",
            dashboard=dashboard_data(user, data),
            charts=chart_data(user, data),
            report=report,
        ),
    )


@router.get("/reports/export.csv")
def export_csv(
    start: str | None = None,
    end: str | None = None,
    type: str | None = None,
    kind: str | None = None,
    category_id: str | None = None,
    payment_method: str | None = None,
    user: dict = Depends(require_user),
):
    effective_type = type or kind
    report = get_report_data(
        user,
        start=start,
        end=end,
        type_filter=effective_type,
        category_id=category_id,
        payment_method=payment_method,
    )

    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Type", "Category", "Amount", "Payment Method", "Note"])
    for tx in report["matching_transactions"]:
        d_val = tx.get("date")
        d_str = d_val.isoformat() if hasattr(d_val, "isoformat") else str(d_val or "")
        cat_name = (tx.get("category") or {}).get("name", "Uncategorized")
        writer.writerow(
            [
                d_str,
                str(tx.get("type", "")).capitalize(),
                cat_name,
                f"{to_decimal(tx.get('amount')):.2f}",
                tx.get("payment_method", ""),
                tx.get("note", ""),
            ]
        )
    output.seek(0)
    store.log_report(str(user["uid"]), f"csv:{effective_type or 'all'}")

    start_part = report["start_date"].isoformat()
    end_part = report["end_date"].isoformat()
    filename = f"dos-report-{start_part}-to-{end_part}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reports/export.pdf")
def export_pdf(
    start: str | None = None,
    end: str | None = None,
    type: str | None = None,
    category_id: str | None = None,
    payment_method: str | None = None,
    user: dict = Depends(require_user),
):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    report = get_report_data(
        user,
        start=start,
        end=end,
        type_filter=type,
        category_id=category_id,
        payment_method=payment_method,
    )

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
        title="D-OS Financial Statement",
    )
    styles = getSampleStyleSheet()

    dos_title_style = ParagraphStyle(
        "DosTitle",
        parent=styles["Title"],
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#030a05"),
        alignment=0,
    )
    dos_subtitle_style = ParagraphStyle(
        "DosSubtitle",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#334438"),
    )
    section_head_style = ParagraphStyle(
        "DosSectionHead",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#030a05"),
        spaceBefore=10,
        spaceAfter=4,
    )
    cell_style = ParagraphStyle(
        "DosCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#112211"),
    )
    cell_bold_style = ParagraphStyle(
        "DosCellBold",
        parent=cell_style,
        fontName="Helvetica-Bold",
    )

    currency = report["currency"]
    story = []

    # 1. Statement Header Banner
    story.append(Paragraph("D-OS FINANCIAL STATEMENT", dos_title_style))
    story.append(
        Paragraph(
            f"User: <b>{user.get('username') or user.get('email') or 'User'}</b> &nbsp;|&nbsp; "
            f"Generated: {datetime.now().strftime('%d %b %Y, %H:%M')} &nbsp;|&nbsp; "
            f"Currency: {currency}",
            dos_subtitle_style,
        )
    )
    story.append(Spacer(1, 6))

    filter_desc = (
        f"<b>Period:</b> {report['period_str']} &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"<b>Type:</b> {report['type_filter'].upper()} &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"<b>Category:</b> {report['category_id']} &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"<b>Payment Method:</b> {report['payment_method']}"
    )
    story.append(Paragraph(filter_desc, dos_subtitle_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#66FF99"), spaceAfter=10))

    # 2. Executive Financial Summary Grid
    story.append(Paragraph("FINANCIAL KPI SUMMARY", section_head_style))
    kpi_rows = [
        [
            Paragraph("<b>METRIC</b>", cell_bold_style),
            Paragraph("<b>AMOUNT</b>", cell_bold_style),
            Paragraph("<b>STATUS / DEFINITION</b>", cell_bold_style),
        ],
        [
            Paragraph("<b>Available Balance</b>", cell_bold_style),
            Paragraph(f"<b>{currency} {report['available_balance']:,.2f}</b>", cell_bold_style),
            Paragraph("Total Income - Total Expenses for period", cell_style),
        ],
        [
            Paragraph("Total Income", cell_style),
            Paragraph(f"{currency} {report['total_income']:,.2f}", cell_style),
            Paragraph("All recorded inflows", cell_style),
        ],
        [
            Paragraph("Total Expenses", cell_style),
            Paragraph(f"{currency} {report['total_expense']:,.2f}", cell_style),
            Paragraph("All recorded outflows", cell_style),
        ],
        [
            Paragraph("Borrowed (Liabilities)", cell_style),
            Paragraph(f"{currency} {report['total_borrowed']:,.2f}", cell_style),
            Paragraph("Money borrowed (liability, not income)", cell_style),
        ],
        [
            Paragraph("Lent (Receivables)", cell_style),
            Paragraph(f"{currency} {report['total_lent']:,.2f}", cell_style),
            Paragraph("Money lent to others (asset, not expense)", cell_style),
        ],
        [
            Paragraph("Debt Repayments", cell_style),
            Paragraph(f"{currency} {report['total_repayments']:,.2f}", cell_style),
            Paragraph("Settled debt balance adjustments", cell_style),
        ],
        [
            Paragraph("Transfers", cell_style),
            Paragraph(f"{currency} {report['total_transfers']:,.2f}", cell_style),
            Paragraph("Intra-account transfers", cell_style),
        ],
    ]
    kpi_table = Table(kpi_rows, colWidths=[150, 140, 230])
    kpi_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0a2412")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#66FF99")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#b3d4bc")),
                ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#eef8f1")),
            ]
        )
    )
    story.append(kpi_table)
    story.append(Spacer(1, 12))

    # 3. Category Breakdown Table
    if report["category_breakdown"]:
        story.append(Paragraph("CATEGORY BREAKDOWN", section_head_style))
        cat_rows = [
            [
                Paragraph("<b>Category</b>", cell_bold_style),
                Paragraph("<b>Transactions</b>", cell_bold_style),
                Paragraph("<b>Amount</b>", cell_bold_style),
                Paragraph("<b>Share (%)</b>", cell_bold_style),
            ]
        ]
        for c in report["category_breakdown"][:12]:
            cat_rows.append(
                [
                    Paragraph(f"{c['name']}", cell_style),
                    Paragraph(str(c["count"]), cell_style),
                    Paragraph(f"{currency} {c['amount']:,.2f}", cell_style),
                    Paragraph(c["pct"], cell_style),
                ]
            )
        cat_table = Table(cat_rows, colWidths=[180, 90, 130, 120])
        cat_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0a2412")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#66FF99")),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#b3d4bc")),
                ]
            )
        )
        story.append(cat_table)
        story.append(Spacer(1, 12))

    # 4. Matching Transactions Table
    story.append(
        Paragraph(
            f"TRANSACTION RECORDS (Showing {min(len(report['matching_transactions']), 60)} of {report['transaction_count']})",
            section_head_style,
        )
    )
    tx_rows = [
        [
            Paragraph("<b>Date</b>", cell_bold_style),
            Paragraph("<b>Type</b>", cell_bold_style),
            Paragraph("<b>Category</b>", cell_bold_style),
            Paragraph("<b>Method</b>", cell_bold_style),
            Paragraph("<b>Amount</b>", cell_bold_style),
            Paragraph("<b>Note</b>", cell_bold_style),
        ]
    ]

    for tx in report["matching_transactions"][:60]:
        d_val = tx.get("date")
        d_str = d_val.strftime("%d %b %Y") if hasattr(d_val, "strftime") else str(d_val or "")
        tx_rows.append(
            [
                Paragraph(d_str, cell_style),
                Paragraph(str(tx.get("type", "")).capitalize(), cell_style),
                Paragraph((tx.get("category") or {}).get("name", "Uncategorized"), cell_style),
                Paragraph(str(tx.get("payment_method") or "—"), cell_style),
                Paragraph(f"{currency} {to_decimal(tx.get('amount')):,.2f}", cell_style),
                Paragraph(str(tx.get("note") or "—")[:35], cell_style),
            ]
        )

    if len(tx_rows) == 1:
        tx_rows.append([Paragraph("No transactions matching configured filters.", cell_style)] + [Paragraph("", cell_style)] * 5)

    tx_table = Table(tx_rows, repeatRows=1, colWidths=[65, 55, 95, 75, 80, 150])
    tx_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0a2412")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#66FF99")),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#c0d9c7")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    story.append(tx_table)

    story.append(Spacer(1, 14))
    story.append(
        Paragraph(
            "Powered by Daivik · Take Control of Every Rupee · D-OS Personal Money Operating System",
            dos_subtitle_style,
        )
    )

    doc.build(story)
    buffer.seek(0)
    store.log_report(str(user["uid"]), "pdf:statement")

    start_part = report["start_date"].isoformat()
    end_part = report["end_date"].isoformat()
    filename = f"dos-report-{start_part}-to-{end_part}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
