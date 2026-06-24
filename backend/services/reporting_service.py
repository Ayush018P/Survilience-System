import os
import datetime
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as RLImage, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

from backend.config import settings

REPORTS_DIR = Path("data/reports")
REPORTS_DIR.mkdir(parents=True, exist_ok=True)

class ReportingService:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=14,
            textColor=colors.darkblue
        )
        self.normal_style = self.styles['Normal']
        self.heading2 = self.styles['Heading2']

    def generate_incident_report(self, event) -> str:
        """Generates a PDF report for a specific event and returns the file path."""
        filename = f"incident_report_{event.id}_{event.timestamp.strftime('%Y%m%d%H%M%S')}.pdf"
        filepath = REPORTS_DIR / filename
        
        doc = SimpleDocTemplate(str(filepath), pagesize=letter)
        story = []

        # Header
        story.append(Paragraph("NeuroGuard AI", self.title_style))
        story.append(Paragraph("Enterprise Security Incident Report", self.heading2))
        story.append(Spacer(1, 0.2 * inch))

        # Basic Info Table
        data = [
            ["Incident ID", f"#{event.id}"],
            ["Date & Time", event.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")],
            ["Person Identified", event.person_name if event.person_name else "Unknown (Stranger)"],
            ["Threat Level", event.threat_level.upper()],
            ["Threat Score", f"{event.threat_score} / 100"],
            ["Threat Type", event.threat_type.title()],
        ]
        
        table = Table(data, colWidths=[2 * inch, 4 * inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.3 * inch))

        # AI Metrics Section
        story.append(Paragraph("Hybrid AI Intelligence Metrics", self.heading2))
        ai_data = [
            ["Metric", "Value"],
            ["CNN Facial Confidence", f"{(event.confidence * 100):.1f}%"],
            ["SNN Spiking Score", f"{(event.snn_score * 100 if event.snn_score else 0):.1f}%"],
            ["Hybrid Stability Risk", "High" if event.stability_score and event.stability_score < 0.6 else "Low / Stable"],
            ["Threat Model Confidence", f"{(event.threat_confidence * 100):.1f}%"],
            ["Temporal Persistence", f"{event.threat_persistence} Frames"],
        ]
        ai_table = Table(ai_data, colWidths=[3 * inch, 3 * inch])
        ai_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0f172a")),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        story.append(ai_table)
        story.append(Spacer(1, 0.4 * inch))

        # Visual Evidence (Snapshot)
        story.append(Paragraph("Visual Evidence (Snapshot)", self.heading2))
        if event.snapshot_path:
            abs_path = os.path.abspath(event.snapshot_path)
            if os.path.exists(abs_path):
                img = RLImage(abs_path)
                # Resize image to fit nicely
                img.drawHeight = 3 * inch
                img.drawWidth = 4 * inch
                story.append(img)
            else:
                story.append(Paragraph(f"Snapshot file missing at: {event.snapshot_path}", self.normal_style))
        else:
            story.append(Paragraph("No snapshot available for this event (No threat or stranger detected at the time).", self.normal_style))
            
        story.append(Spacer(1, 0.5 * inch))
        story.append(Paragraph("Generated automatically by NeuroGuard AI Security Intelligence Platform.", self.styles['Italic']))

        # Build PDF
        doc.build(story)
        return str(filepath)

reporting_service = ReportingService()
