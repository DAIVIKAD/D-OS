from __future__ import annotations

import csv
from datetime import date
from io import BytesIO, StringIO

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.core.templates import templates
from app.core.view import context
from app.firebase.auth import require_user
from app.services import firestore_service as store
from app.services.finance import chart_data, dashboard_data, prefetch_data, transaction_query

router = APIRouter()


@router.get("/reports")
def reports_page(request: Request, user: dict = Depends(require_user)):
    data = prefetch_data(user)
    return templates.TemplateResponse(
        "pages/reports.html",
        context(
            request,
            user,
            page_title="Reports",
            dashboard=dashboard_data(user, data),
            charts=chart_data(user, data),
        ),
    )


@router.get("/reports/export.csv")
def export_csv(kind: str | None = None, user: dict = Depends(require_user)):
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Type", "Category", "Amount", "Payment Method", "Note"])
    for tx in transaction_query(user, kind=kind):
        writer.writerow(
            [
                tx["date"].isoformat() if hasattr(tx.get("date"), "isoformat") else tx.get("date", ""),
                tx.get("type", ""),
                (tx.get("category") or {}).get("name", "Uncategorized"),
                f"{tx.get('amount', 0):.2f}",
                tx.get("payment_method", ""),
                tx.get("note", ""),
            ]
        )
    output.seek(0)
    store.log_report(str(user["uid"]), f"csv:{kind or 'money'}")
    filename = f"dos-{kind or 'money'}-{date.today().isoformat()}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/reports/export.pdf")
def export_pdf(user: dict = Depends(require_user)):
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, title="D OS Finance Report")
    styles = getSampleStyleSheet()
    data = prefetch_data(user, include_investments=False)
    dashboard = dashboard_data(user, data)
    transactions = data["transactions"][:25]
    currency = str(user.get("currency", "₹"))
    story = [
        Paragraph("D OS Finance Report", styles["Title"]),
        Paragraph("Powered by Daivik · Take Control of Every Rupee.", styles["Normal"]),
        Spacer(1, 14),
        Table(
            [
                ["Monthly Income", f"{currency}{dashboard['monthly_income']:,.2f}"],
                ["Monthly Expense", f"{currency}{dashboard['monthly_expense']:,.2f}"],
                ["Remaining Budget", f"{currency}{dashboard['remaining_budget']:,.2f}"],
                ["Savings", f"{currency}{dashboard['savings']:,.2f}"],
            ],
            colWidths=[180, 220],
        ),
        Spacer(1, 18),
        Paragraph("Recent Transactions", styles["Heading2"]),
    ]
    rows = [["Date", "Type", "Category", "Amount", "Note"]]
    rows.extend(
        [
            [
                tx["date"].isoformat() if hasattr(tx.get("date"), "isoformat") else tx.get("date", ""),
                str(tx.get("type", "")).title(),
                (tx.get("category") or {}).get("name", "Uncategorized"),
                f"{currency}{tx.get('amount', 0):,.2f}",
                str(tx.get("note", ""))[:40],
            ]
            for tx in transactions
        ]
    )
    table = Table(rows, repeatRows=1, colWidths=[70, 65, 95, 90, 170])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.black),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.limegreen),
                ("GRID", (0, 0), (-1, -1), 0.3, colors.grey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    story.append(table)
    doc.build(story)
    buffer.seek(0)
    store.log_report(str(user["uid"]), "pdf:finance")
    filename = f"dos-report-{date.today().isoformat()}.pdf"
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
