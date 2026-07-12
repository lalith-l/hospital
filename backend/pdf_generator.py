from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.platypus import Image as RLImage
import io
import os
import qrcode

def generate_medical_report(session_data: dict) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=50, leftMargin=50, topMargin=50, bottomMargin=50)
    
    styles = getSampleStyleSheet()
    title_style = styles['Heading1']
    title_style.alignment = 1 # Center
    
    h2_style = styles['Heading2']
    h2_style.textColor = colors.HexColor("#2563eb") # Tailwind blue-600
    
    normal_style = styles['Normal']
    
    elements = []
    
    # Title
    elements.append(Paragraph("Predictive Patient Pathfinder - Medical Triage Report", title_style))
    elements.append(Spacer(1, 10))
    
    # QR Code
    session_id = session_data.get("session_id")
    if session_id:
        frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:5173").rstrip("/")
        qr_url = f"{frontend_url}/hospital/session/{session_id}"
        qr = qrcode.QRCode(version=1, box_size=5, border=2)
        qr.add_data(qr_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")
        
        qr_buffer = io.BytesIO()
        img.save(qr_buffer, format="PNG")
        qr_buffer.seek(0)
        
        rl_img = RLImage(qr_buffer, width=100, height=100)
        rl_img.hAlign = 'CENTER'
        elements.append(rl_img)
        
        qr_sub_style = ParagraphStyle("QRSub", parent=normal_style, alignment=1, fontSize=8, textColor=colors.gray)
        elements.append(Paragraph("Hospital Scan to load session context", qr_sub_style))
        elements.append(Spacer(1, 20))
    else:
        elements.append(Spacer(1, 20))
    
    # 1. Final Conclusion
    elements.append(Paragraph("1. Triage Conclusion", h2_style))
    elements.append(Spacer(1, 10))
    
    result = session_data.get("triageResult", {})
    
    urgency_map = {1: "Critical", 2: "Urgent", 3: "Routine"}
    urgency_level = result.get("urgency", 3)
    
    summary_data = [
        ["Predicted Condition", result.get("condition", "Unknown")],
        ["Urgency Level", f"Level {urgency_level} - {urgency_map.get(urgency_level, 'Routine')}"],
        ["Geographical Risk", result.get("elevated_risk", "N/A")]
    ]
    
    t = Table(summary_data, colWidths=[150, 300])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (1, -1), colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.grey)
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))
    
    # 2. Recommended Hospital
    hospital = result.get("recommended_hospital")
    if hospital:
        elements.append(Paragraph("2. Hospital Routing", h2_style))
        elements.append(Spacer(1, 10))
        hosp_data = [
            ["Hospital Name", hospital.get("name", "N/A")],
            ["Distance", hospital.get("distance", "N/A")],
            ["Current Load", hospital.get("current_load", "N/A")]
        ]
        ht = Table(hosp_data, colWidths=[150, 300])
        ht.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey)
        ]))
        elements.append(ht)
        elements.append(Spacer(1, 20))
        

    # 3. Chat Transcript
    messages = session_data.get("messages", [])
    if messages:
        elements.append(Paragraph("3. Patient Transcript", h2_style))
        elements.append(Spacer(1, 10))
        
        for m in messages:
            role = m.get("role", "unknown").capitalize()
            content = m.get("content", "")
            
            p_style = ParagraphStyle(
                "Chat",
                parent=normal_style,
                spaceAfter=10,
                leftIndent=20 if role == "Assistant" else 0,
                textColor=colors.darkblue if role == "Assistant" else colors.black
            )
            elements.append(Paragraph(f"<b>{role}:</b> {content}", p_style))
            
    doc.build(elements)
    buffer.seek(0)
    return buffer
