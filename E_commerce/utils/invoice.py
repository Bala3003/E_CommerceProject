from io import BytesIO
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
from reportlab.lib.styles import getSampleStyleSheet

def generate_invoice_pdf(order, company_name="E-Shop"):
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                            rightMargin=20*mm, leftMargin=20*mm,
                            topMargin=20*mm, bottomMargin=20*mm)
    styles = getSampleStyleSheet()
    elems = []

    elems.append(Paragraph(f"<b>{company_name}</b>", styles['Title']))
    elems.append(Spacer(1, 12))
    elems.append(Paragraph(f"<b>Invoice # {order.id}</b>", styles['Heading3']))
    elems.append(Paragraph(f"Customer: {order.full_name}", styles['Normal']))
    elems.append(Paragraph(f"Phone: {order.phone}", styles['Normal']))
    elems.append(Paragraph(
        f"Address: {order.address_line1}, {order.city}, {order.state} - {order.postal_code}",
        styles['Normal']
    ))
    elems.append(Spacer(1, 12))

    # ===== Items Table =====
    data = [["#", "Product", "Price", "Qty", "Subtotal"]]
    total = 0.0

    for i, item in enumerate(order.items.all(), start=1):
        subtotal = float(item.subtotal)
        total += subtotal
        data.append([
            i,
            item.product.name,
            f"Rs. {item.price:.2f}",
            item.quantity,
            f"Rs. {subtotal:.2f}"
        ])

    data.append(["", "", "", "Total", f"Rs. {total:.2f}"])

    table = Table(data, colWidths=[20*mm, 70*mm, 25*mm, 20*mm, 30*mm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.lightblue),
        ("ALIGN", (2, 1), (-1, -1), "RIGHT"),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (3, -1), (4, -1), "Helvetica-Bold"),  # bold total row
        ("BACKGROUND", (3, -1), (4, -1), colors.whitesmoke),
    ]))
    elems.append(table)

    elems.append(Spacer(1, 12))
    elems.append(Paragraph("Thank you for shopping with E-Shop!", styles['Italic']))

    doc.build(elems)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
